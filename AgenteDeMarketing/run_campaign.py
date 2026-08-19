"""
Principal interactive terminal script to run the Multi-Agent Marketing Campaign.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt

# Cargar dotenv para asegurarse de que las variables están en el entorno
load_dotenv()

# Añadir el directorio 'src' al path de python para poder importar el paquete local
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

try:
    from agente_ventas.graph import graph
except ImportError as e:
    print(f"Error al importar el grafo del agente: {str(e)}")
    print("Asegúrate de que estás ejecutando el script desde la raíz de 'AgenteDeVentas' y que las dependencias están instaladas.")
    sys.exit(1)

console = Console()

def print_banner():
    console.print("\n")
    console.print(Panel.fit(
        "[bold cyan]🚀 SISTEMA AGÉNTICO DE MARKETING Y VENTAS AUTOMATIZADAS 🚀[/bold cyan]\n"
        "[dim]Orquestado por LangGraph, alimentado por OpenRouter y LightPanda[/dim]",
        border_style="cyan"
    ))
    console.print("\n")

def get_report_path() -> Path:
    root = Path(__file__).resolve().parent
    return root / "resultado_campana.txt"


def format_final_report(report: dict) -> str:
    parts = [
        "CAMPAÑA DE MARKETING - RESULTADO FINAL",
        "======================================",
        f"Producto: {report['product_description']}",
        f"Motivo de finalización: {report['completion_reason']}",
        "",
    ]

    if report["market_research"]:
        parts.extend([
            "=== REPORTE DE INVESTIGACIÓN DE MERCADO ===",
            report["market_research"],
            "",
        ])

    if report["seo_channels_plan"]:
        parts.extend([
            "=== PLAN ESTRATÉGICO Y SEO ===",
            report["seo_channels_plan"],
            "",
        ])

    if report["copywriting_drafts"]:
        parts.append("=== BORRADORES DE COPY PERSUASIVO (ÚLTIMO) ===")
        for key, val in report["copywriting_drafts"].items():
            parts.extend([
                f"--- {key.upper()} ---",
                val,
                "",
            ])

    # Entregas acumuladas por agente (cronología)
    if report.get("node_deliveries"):
        parts.append("=== ENTREGAS POR AGENTE (HASTA FINALIZACIÓN) ===")
        agents_order = ["supervisor", "investigador", "estratega", "copywriter"]
        for agent in agents_order:
            deliveries = report["node_deliveries"].get(agent, [])
            parts.append(f"--- Agente: {agent.upper()} (entregas totales: {len(deliveries)}) ---")
            if not deliveries:
                parts.append("  (sin entregas)")
                parts.append("")
                continue
            # Mostrar TODAS las entregas de este agente
            for i, d in enumerate(deliveries, 1):
                parts.append(f"[Entrega {i}/{len(deliveries)}]")
                ordered_keys = ["completion_reason", "supervisor_feedback", "market_research", "seo_channels_plan", "copywriting_drafts", "messages"]
                for k in ordered_keys:
                    if k in d:
                        v = d[k]
                        parts.append(f"{k}:")
                        if isinstance(v, dict):
                            for subk, subv in v.items():
                                parts.append(f"  {subk}:")
                                for line in str(subv).splitlines():
                                    parts.append(f"    {line}")
                        elif isinstance(v, list):
                            for item in v:
                                for line in str(item).splitlines():
                                    parts.append(f"  {line}")
                        else:
                            for line in str(v).splitlines():
                                parts.append(f"  {line}")
                for k, v in d.items():
                    if k in ordered_keys:
                        continue
                    parts.append(f"{k}:")
                    for line in str(v).splitlines():
                        parts.append(f"  {line}")
                parts.append("")

    if report["messages"]:
        parts.append("=== MENSAJES DEL FLUJO ===")
        for msg in report["messages"]:
            content = getattr(msg, "content", None) or str(msg)
            parts.append(content)
        parts.append("")

    return "\n".join(parts)


def write_final_report(report: dict):
    path = get_report_path()
    text = format_final_report(report)
    path.write_text(text, encoding="utf-8")


def run_campaign():
    print_banner()
    
    # 1. Solicitar el producto o servicio al usuario
    product = Prompt.ask(
        "[bold yellow]¿Qué producto o servicio deseas promocionar hoy?[/bold yellow]"
    )
    
    if not product.strip():
        console.print("[bold red]El producto no puede estar vacío. Saliendo...[/bold red]")
        return
        
    # 2. Configurar el estado inicial
    initial_state = {
        "product_description": product,
        "messages": [],
        "market_research": "",
        "seo_channels_plan": "",
        "copywriting_drafts": {},
        "supervisor_feedback": "",
        "next_agent": "",
        "completion_reason": "",
        "agent_call_counts": {},
    }
    
    # Acumulador de resultados para exportar al finalizar
    final_report = {
        "product_description": product,
        "market_research": "",
        "seo_channels_plan": "",
        "copywriting_drafts": {},
        "messages": [],
        "completion_reason": "",
        "node_deliveries": {},
    }

    # Configurar el hilo de ejecución para la persistencia de memoria
    config = {"configurable": {"thread_id": "campana_marketing_ventas_1"}}
    
    console.print(f"\n[bold green]Iniciando la campaña para:[/bold green] '{product}'\n")
    console.print("[dim]Orquestando nodos en tiempo real...[/dim]\n")
    
    # 3. Stream del grafo de LangGraph
    try:
        for event in graph.stream(initial_state, config):
            for node_name, output in event.items():
                console.print(Panel(
                    f"[bold white]Ejecutando nodo:[/bold white] [bold magenta]{node_name.upper()}[/bold magenta]",
                    border_style="magenta"
                ))
                
                # Acumular el estado final para exportar al archivo
                if "market_research" in output and output["market_research"]:
                    final_report["market_research"] = output["market_research"]
                if "seo_channels_plan" in output and output["seo_channels_plan"]:
                    final_report["seo_channels_plan"] = output["seo_channels_plan"]
                if "copywriting_drafts" in output and output["copywriting_drafts"] and isinstance(output["copywriting_drafts"], dict):
                    final_report["copywriting_drafts"] = output["copywriting_drafts"]
                if "completion_reason" in output and output["completion_reason"]:
                    final_report["completion_reason"] = output["completion_reason"]
                if "messages" in output and output["messages"]:
                    final_report["messages"].extend(output["messages"])

                # Registrar la entrega del nodo (acumulando cronología)
                node_hist = final_report.setdefault("node_deliveries", {})
                snapshot = {}
                for k, v in output.items():
                    if k == "messages" and isinstance(v, list):
                        snapshot[k] = [getattr(m, "content", str(m)) for m in v]
                    else:
                        snapshot[k] = v
                node_hist.setdefault(node_name, []).append(snapshot)

                # Imprimir el mensaje de registro del agente si existe
                if "messages" in output and output["messages"]:
                    last_msg = output["messages"][-1]
                    console.print(f"[bold yellow]Registro de Actividad:[/bold yellow] {last_msg.content}\n")

                # Si el Investigador entregó su reporte, mostrarlo estructurado
                if "market_research" in output and output["market_research"]:
                    console.print(Panel(
                        Markdown(output["market_research"]),
                        title="[bold green]🔍 REPORTE DE INVESTIGACIÓN DE MERCADO[/bold green]",
                        border_style="green"
                    ))
                    console.print("\n")
                    
                # Si el Estratega entregó su plan de SEO/Canales, mostrarlo estructurado
                if "seo_channels_plan" in output and output["seo_channels_plan"]:
                    console.print(Panel(
                        Markdown(output["seo_channels_plan"]),
                        title="[bold blue]📈 PLAN ESTRATÉGICO Y SEO[/bold blue]",
                        border_style="blue"
                    ))
                    console.print("\n")
                    
                # Si el Copywriter entregó sus borradores de textos, mostrarlos estructurados
                if "copywriting_drafts" in output and output["copywriting_drafts"] and isinstance(output["copywriting_drafts"], dict):
                    drafts = output["copywriting_drafts"]
                    console.print("[bold yellow]✍️ BORRADORES DE COPY PERSUASIVO GENERADOS:[/bold yellow]")
                    for key, val in drafts.items():
                        console.print(Panel(
                            val,
                            title=f"[bold yellow]Pieza: {key.upper()}[/bold yellow]",
                            border_style="yellow"
                        ))
                    console.print("\n")
                    
    except Exception as e:
        console.print(f"\n[bold red]Ocurrió un error durante la ejecución del grafo:[/bold red] {str(e)}")
        console.print("[yellow]Verifica que tus llaves de API en .env sean válidas y que LightPanda en Docker esté corriendo.[/yellow]")
        write_final_report(final_report)
        console.print(f"[bold green]Se guardó el reporte parcial en el archivo:[/bold green] {get_report_path()}")
        return

    write_final_report(final_report)
    console.print(Panel(
        "[bold green]🎉 ¡CAMPAÑA COMPLETADA CON ÉXITO! 🎉[/bold green]\n"
        "El supervisor (CMO) ha verificado los entregables y ha dado el visto bueno final.",
        border_style="green"
    ))

if __name__ == "__main__":
    run_campaign()
