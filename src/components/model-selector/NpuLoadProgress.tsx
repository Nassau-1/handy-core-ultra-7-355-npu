import { useEffect, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { useTranslation } from "react-i18next";
import { Button } from "../ui/Button";

interface LoadProgress {
  stage: string;
  elapsed_ms: number;
  active: boolean;
  error: string | null;
}

export default function NpuLoadProgress() {
  const { t } = useTranslation();
  const [progress, setProgress] = useState<LoadProgress | null>(null);
  const [cancelling, setCancelling] = useState(false);
  const [commandError, setCommandError] = useState<string | null>(null);

  useEffect(() => {
    let disposed = false;
    let receivedEvent = false;
    let unlisten: (() => void) | undefined;
    const receive = (value: LoadProgress | null) => {
      if (disposed) return;
      setProgress(value);
      if (!value?.active || value.stage === "starting") {
        setCancelling(false);
        setCommandError(null);
      }
    };
    void (async () => {
      unlisten = await listen<LoadProgress>("npu-load-progress", (event) => {
        receivedEvent = true;
        receive(event.payload);
      });
      if (disposed) {
        unlisten();
        return;
      }
      const snapshot = await invoke<LoadProgress | null>("get_npu_load_status");
      if (!receivedEvent) receive(snapshot);
    })().catch(console.error);
    return () => {
      disposed = true;
      unlisten?.();
    };
  }, []);

  if (!progress || progress.stage === "ready") return null;
  const stages = [
    "starting",
    "importing",
    "checking_driver",
    "detecting",
    "compiling",
    "cancelled",
    "failed",
  ];
  const stage = stages.includes(progress.stage) ? progress.stage : "starting";
  const cancel = async () => {
    setCancelling(true);
    setCommandError(null);
    try {
      const accepted = await invoke<boolean>("cancel_npu_load");
      if (!accepted) {
        setCancelling(false);
        setProgress(await invoke<LoadProgress | null>("get_npu_load_status"));
      }
    } catch (error) {
      setCancelling(false);
      setCommandError(String(error));
    }
  };

  return (
    <div className="fixed bottom-16 left-4 right-4 z-50 mx-auto max-w-xl rounded-xl border border-mid-gray/40 bg-background p-4 shadow-lg">
      <p role="status" aria-live="polite" className="text-sm font-medium">
        {t(`npuLoading.stages.${stage}`)}
        {progress.active &&
          ` · ${t("npuLoading.elapsed", { seconds: Math.floor(progress.elapsed_ms / 1000) })}`}
      </p>
      {progress.active && (
        <p className="mt-1 text-xs text-text/60">{t("npuLoading.hint")}</p>
      )}
      {(commandError || (progress.stage === "failed" && progress.error)) && (
        <p
          role="alert"
          className="mt-2 max-h-32 overflow-auto break-words text-sm text-text/80"
        >
          {commandError || progress.error}
        </p>
      )}
      <div className="mt-3">
        {progress.active ? (
          <Button
            variant="secondary"
            size="sm"
            disabled={cancelling}
            onClick={cancel}
          >
            {t(cancelling ? "npuLoading.cancelling" : "npuLoading.cancel")}
          </Button>
        ) : (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setProgress(null)}
          >
            {t("npuLoading.dismiss")}
          </Button>
        )}
      </div>
    </div>
  );
}
