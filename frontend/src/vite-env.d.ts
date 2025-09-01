/// <reference types="vite/client" />

declare interface ImportMetaEnv {
  readonly VITE_BACKEND_URL?: string;
  readonly REACT_APP_BACKEND_URL?: string;
}

declare interface ImportMeta {
  readonly env: ImportMetaEnv;
}
