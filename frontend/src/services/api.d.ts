export declare const api: import('axios').AxiosInstance;
export declare const fetchState: () => Promise<any>;
export declare const postChat: (q: string) => Promise<any>;
export declare const postVision: (form: FormData, groundingRequired: boolean) => Promise<any>;
export declare const getApprovals: () => Promise<any>;
export declare const approveProposal: (id: number) => Promise<any>;
export declare const denyProposal: (id: number) => Promise<any>;
export declare const getAdaptersState: () => Promise<any>;
export declare const promoteAdapter: (role: string) => Promise<any>;
export declare const getGovernor: () => Promise<any>;
export declare const setGovernor: (enabled: boolean, force_deepseek_r1: boolean) => Promise<any>;
export declare const health: () => Promise<{
  ok: boolean;
  data: any;
}>;
export declare const startTraining: () => Promise<any>;
export declare const previewAutopromote: () => Promise<any>;
export declare const getSecretsHealth: () => Promise<any>;
export declare const secretExists: (name: string) => Promise<{
  name: string;
  exists: boolean;
}>;
export declare const setSecret: (
  name: string,
  value: any,
  adminToken?: string
) => Promise<{
  status?: string;
  error?: string;
  provider?: string;
}>;
export declare const reloadRouterSecrets: (adminToken?: string) => Promise<{
  status?: string;
  error?: string;
}>;
export declare const warmQwenProvider: (adminToken?: string) => Promise<{
  status?: string;
  error?: string;
  provider?: string;
  model?: string;
}>;
export declare const getProvidersStatus: () => Promise<{
  providers?: Record<string, any>;
  router_active?: boolean;
  timestamp?: number;
  error?: string;
}>;
export declare const getCacheHealth: () => Promise<any>;
export declare const getCacheAnalytics: () => Promise<any>;
export declare const clearCache: (pattern?: string, adminToken?: string) => Promise<any>;
export declare const getCacheStatus: () => Promise<any>;
export declare const getCacheReport: () => Promise<any>;
export declare const optimizeCache: (targetHitRate: number) => Promise<any>;
export declare const warmCache: () => Promise<any>;
export declare const setRouterThresholds: (
  params: Partial<{
    conf_threshold: number;
    support_threshold: number;
    max_cot_tokens: number;
  }>,
  adminToken?: string
) => Promise<{
  status?: string;
  current_thresholds?: any;
  error?: string;
}>;
export declare const getSwarmStatus: () => Promise<any>;
//# sourceMappingURL=api.d.ts.map
