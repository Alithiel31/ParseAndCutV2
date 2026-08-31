import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "../i18n";

interface LegalPageProps {
  title: string;
  updatedAt: string;
  children: ReactNode;
}

export default function LegalPage({ title, updatedAt, children }: LegalPageProps) {
  const { t } = useTranslation();

  return (
    <main className="card">
      {/* React 19 remonte automatiquement <title> dans le <head> */}
      <title>{`${title} · ${t("meta.appName")}`}</title>

      <div className="result-header">
        <h2>{title}</h2>
        <Link to="/" className="btn-secondary legal-back">{t("common.back")}</Link>
      </div>

      <p className="legal-updated">{t("legal.updatedAt", { date: updatedAt })}</p>

      <div className="markdown-body">{children}</div>
    </main>
  );
}
