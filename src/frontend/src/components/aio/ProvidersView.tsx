import { useAioStore } from "./AioStore";
import AioProviderCard from "./AioProviderCard";

function ProvidersView() {
  const { providers, health } = useAioStore();

  if (providers.length === 0) {
    return <div className="aio-empty">No providers configured</div>;
  }

  return (
    <div className="aio-providers-grid">
      {providers.map((p) => (
        <AioProviderCard key={p.id} provider={p} health={health[p.id]} />
      ))}
    </div>
  );
}

export default ProvidersView;
