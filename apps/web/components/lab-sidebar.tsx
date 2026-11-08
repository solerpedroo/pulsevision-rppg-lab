import Link from "next/link";
import {
  Activity,
  Video,
  Radio,
  FlaskConical,
  ShieldCheck,
} from "lucide-react";
import { APP_VERSION } from "@/lib/release";
const labs = [
  { id: "video", name: "Video Lab", number: "01", icon: Video },
  { id: "live", name: "Live Lab", number: "02", icon: Radio },
  { id: "benchmark", name: "Benchmark", number: "03", icon: FlaskConical },
] as const;
export function LabSidebar({
  active,
}: {
  active: "video" | "live" | "benchmark";
}) {
  const notice =
    active === "live"
      ? {
          title: "Processamento no navegador.",
          body: "Frames não são enviados. Stop libera câmera, worker e séries da sessão.",
        }
      : active === "benchmark"
        ? {
            title: "Resultados com origem.",
            body: "Inspeção de arquivos locais. Sem upload ou execução de experimento nesta tela.",
          }
        : {
            title: "Local por princípio.",
            body: "Arquivos escolhidos por você. Resultados experimentais, com rastreabilidade.",
          };
  return (
    <aside className="sidebar">
      <Link href="/video" className="brand">
        <span className="brand-mark">
          <Activity size={24} />
        </span>
        <span>
          PulseVision<small>rPPG RESEARCH LAB</small>
        </span>
      </Link>
      <p className="nav-label">WORKSPACE</p>
      <nav aria-label="Laboratórios">
        {labs.map((lab) => (
          <Link
            key={lab.id}
            href={`/${lab.id}`}
            aria-label={`${lab.name} ${lab.number}`}
            aria-current={active === lab.id ? "page" : undefined}
            className={`nav-item ${active === lab.id ? "selected" : ""}`}
          >
            <lab.icon size={18} />
            <span>{lab.name}</span> <span>{lab.number}</span>
          </Link>
        ))}
      </nav>
      <div className="sidebar-bottom">
        <ShieldCheck size={21} />
        <strong>{notice.title}</strong>
        <p>{notice.body}</p>
        <span className="mono">v{APP_VERSION} · EXPERIMENTAL</span>
      </div>
    </aside>
  );
}
