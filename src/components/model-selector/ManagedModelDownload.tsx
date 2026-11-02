import React from "react";
import { useTranslation } from "react-i18next";
import { useModelStore } from "../../stores/modelStore";
import { Button } from "../ui/Button";
import modelLock from "../../../packaging/managed-model-lock.json";

/** Only the embedded, owner-approved HF snapshot is offered. */
export const ManagedModelDownload: React.FC = () => {
  const { t } = useTranslation();
  const {
    downloadingModels,
    verifyingModels,
    downloadProgress,
    downloadModel,
    cancelDownload,
    error,
  } = useModelStore();
  const id = modelLock.model_id;
  const downloading = id in downloadingModels;
  const percent = Math.floor(downloadProgress[id]?.percentage ?? 0);
  if (!modelLock.repo || !modelLock.revision) {
    return <p role="status">{t("managed.awaitingPublication")}</p>;
  }
  return (
    <div className="space-y-2 text-sm">
      {downloading ? (
        <>
          <p role="status">
            {t(
              id in verifyingModels
                ? "managed.verifying"
                : "managed.downloadProgress",
              { percent },
            )}
          </p>
          <progress
            className="w-full"
            max={100}
            value={percent}
            aria-label={t("managed.downloadProgress", { percent })}
          />
          <Button onClick={() => cancelDownload(id)}>
            {t("managed.cancelDownload")}
          </Button>
        </>
      ) : (
        <Button onClick={() => downloadModel(id)}>
          {t("managed.download")}
        </Button>
      )}
      {error && (
        <p role="alert" className="text-red-500">
          {error}
        </p>
      )}
    </div>
  );
};
