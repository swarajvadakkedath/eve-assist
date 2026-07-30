# Code Signing

## Overview

Code signing establishes trust for Eve Desktop executables on Windows. Without signing, Windows SmartScreen shows "Unknown publisher" warnings, and antivirus software may flag the installer as suspicious. Code signing is currently **disabled** — this document describes how to enable it.

## Certificate Types

| Type | Cost | Validation | Trust Level |
|------|------|------------|-------------|
| **EV (Extended Validation)** | $200-500/year | Company identity verified | ✅ Immediate SmartScreen reputation |
| **OV (Organization Validation)** | $100-300/year | Company identity verified | ✅ Builds reputation over time |
| **Individual** | $50-200/year | Personal identity | ⚠️ Slower reputation building |

**Recommendation**: OV certificate from a major CA (DigiCert, Sectigo, GlobalSign) for the initial release. EV certificate after product-market fit.

## Certificate Storage

| Environment | Storage Location | Access |
|-------------|------------------|--------|
| Local dev | CurrentUser/My certificate store | Developer's Windows user account |
| CI/CD (GitHub Actions) | GitHub Secrets (base64-encoded .pfx) | `${{ secrets.SIGNING_CERT }}` |
| CI/CD (Azure Key Vault) | Azure Key Vault (recommended for EV) | OIDC authentication |

## Signing Tools

### signtool.exe (Windows SDK)

```powershell
# Install Windows SDK (includes signtool)
winget install "Windows SDK" --source msstore

# Sign a single file
signtool sign /fd SHA256 /a /f certificate.pfx /p "$PASSWORD" /tr http://timestamp.digicert.com /td SHA256 eve-desktop.exe

# Sign the installer
signtool sign /fd SHA256 /a /f certificate.pfx /p "$PASSWORD" /tr http://timestamp.digicert.com /td SHA256 Eve_1.0.0_x64-setup.exe

# Timestamp only (for previously signed files)
signtool timestamp /tr http://timestamp.digicert.com /td SHA256 eve-desktop.exe

# Verify signature
signtool verify /v /pa eve-desktop.exe
```

### Azure Code Signing (Recommended for CI/CD)

```powershell
# Using Azure Trusted Signing (no certificate import needed)
# Requires: Azure subscription + Trusted Signing account
signtool sign /fd SHA256 /a /tr http://timestamp.acs.microsoft.com /td SHA256 /v ^
  /dlib "C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\AzureSignLimitedExperience\AzureCodeSignLimitedExperience.dll" ^
  /dm "ClientId=<client-id>" ^
  /du "https://eveos.ai" ^
  /dkv "https://eus.codesigning.azure.net" ^
  /dac "AccountName=<account>" /dac "CertificateProfile=<profile>" ^
  eve-desktop.exe
```

## Integration into Build Pipeline

### Manual Signing (Local Builds)

```powershell
# After npm run eve:build, sign the outputs
signtool sign /fd SHA256 /a /f C:\certificates\eve.pfx /p $env:PFX_PASSWORD /tr http://timestamp.digicert.com /td SHA256 ^
  desktop/src-tauri/target/release/eve-desktop.exe

signtool sign /fd SHA256 /a /f C:\certificates\eve.pfx /p $env:PFX_PASSWORD /tr http://timestamp.digicert.com /td SHA256 ^
  desktop/src-tauri/target/release/bundle/nsis/Eve_1.0.0_x64-setup.exe
```

### CI/CD Signing (GitHub Actions)

The existing `.github/workflows/release.yml` has a signing step placeholder:

```yaml
- name: Sign installer
  if: ${{ secrets.SIGNING_CERT != '' }}
  shell: pwsh
  run: |
    echo "$env:SIGNING_CERT" | base64 --decode > certificate.pfx
    & 'C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe' sign ^
      /fd SHA256 /a /f certificate.pfx /p "$env:SIGNING_PASSWORD" ^
      /tr http://timestamp.digicert.com /td SHA256 ^
      desktop/src-tauri/target/release/eve-desktop.exe
    & 'C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe' sign ^
      /fd SHA256 /a /f certificate.pfx /p "$env:SIGNING_PASSWORD" ^
      /tr http://timestamp.digicert.com /td SHA256 ^
      desktop/src-tauri/target/release/bundle/nsis/Eve_*.exe
```

## Files to Sign

| File | Why Sign |
|------|----------|
| `eve-desktop.exe` | Main application binary — users run this directly |
| `Eve_1.0.0_x64-setup.exe` | Installer — SmartScreen checks this first |
| `python/python.exe` (optional) | Embedded Python — not typically signed but improves trust |
| `python/pythonw.exe` (optional) | Embedded Python (windowless) |

## SmartScreen Reputation

Even with a valid signature, SmartScreen may show warnings until enough users have run the application. To accelerate reputation:

1. **Submit to Microsoft Defender portal**: https://www.microsoft.com/en-us/wdsi/filesubmission
2. **Distribute to early adopters**: Each clean install builds reputation
3. **Use EV certificate**: Bypasses SmartScreen reputation delay

## Checklist (Pre-Signing)

- [ ] Acquire code signing certificate (OV or EV)
- [ ] Install certificate in CI/CD secret store (GitHub Secrets or Azure Key Vault)
- [ ] Install Windows SDK on build machine (signtool)
- [ ] Update `.github/workflows/release.yml` with signing step
- [ ] Test signing locally before CI/CD
- [ ] Verify signed binary: `signtool verify /v /pa eve-desktop.exe`
- [ ] Submit signed installer to Microsoft Defender portal
- [ ] Update documentation with certificate expiry date
- [ ] Set calendar reminder for certificate renewal (1 year before expiry)

## Security Considerations

- **Private key protection**: Never store the private key in source code. Use CI/CD secrets or hardware security module.
- **Revocation**: If the certificate is compromised, revoke immediately via your CA's portal.
- **Timestamping**: Always use RFC 3161 timestamping (`/tr`) so signatures remain valid after certificate expiry.
- **Dual signing**: For Windows 7 compatibility, sign with SHA-1 + SHA-256. For Windows 10+, SHA-256 only.
