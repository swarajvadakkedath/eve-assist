import type { ReactNode, HTMLAttributes } from "react";

export interface PageContainerProps extends HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  full?: boolean;
}

function PageContainer({ children, full = false, className = "", ...rest }: PageContainerProps) {
  return (
    <div
      className={`pr-page-container${full ? " pr-page-container-full" : ""} ${className}`.trim()}
      role="region"
      {...rest}
    >
      {children}
    </div>
  );
}

export default PageContainer;
