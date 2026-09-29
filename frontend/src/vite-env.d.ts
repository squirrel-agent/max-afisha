/// <reference types="vite/client" />

interface MaxWebAppBridge {
  initData?: string;
  initDataUnsafe?: Record<string, unknown>;
  platform?: string;
  ready?: () => void;
  expand?: () => void;
}

interface Window {
  WebApp?: MaxWebAppBridge;
}
