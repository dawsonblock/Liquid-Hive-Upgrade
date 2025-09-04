declare global {
  interface Window {
    __APP_CONFIG__?: {
      backendUrl?: string;
    };
  }
}
export declare function getBackendHttpBase(): string;
export declare function getBackendWsBase(): string;
//# sourceMappingURL=env.d.ts.map
