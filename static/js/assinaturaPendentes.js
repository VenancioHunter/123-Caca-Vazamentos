// =============================================================
// Página do técnico: assina relatórios pendentes com a assinatura
// digital avançada e estampa um carimbo padronizado no PDF.
// =============================================================

document.addEventListener("DOMContentLoaded", async function () {
  if (!window.AdvancedSignatureComponent) {
    console.error("Componente de assinatura avançada não carregado.");
    return;
  }

  const componente = new window.AdvancedSignatureComponent({
    namespace: "relatorio_tecnico",
    containerSelector: "#advanced-signature-component",
    autoPromptRegister: true,
    requireSignature: true,
  });

  try {
    await componente.init();
  } catch (error) {
    console.error("Falha ao iniciar assinatura avançada:", error);
  }

  document.querySelectorAll("[data-sign-button]").forEach((botao) => {
    botao.addEventListener("click", () =>
      assinarRelatorio(botao, componente).catch((error) => {
        console.error("Falha ao assinar relatório:", error);
        definirFeedback(
          botao,
          error.message || "Erro ao assinar o relatório.",
          "danger",
        );
        botao.disabled = false;
        botao.textContent = "Assinar";
      }),
    );
  });
});

function definirFeedback(botao, mensagem, tom = "secondary") {
  const linha = botao.closest("[data-report-row]");
  const node = linha ? linha.querySelector("[data-sign-feedback]") : null;
  if (!node) return;
  const cores = {
    success: "#1d7d46",
    danger: "#b42318",
    info: "#0d5590",
    secondary: "#5b6470",
  };
  node.textContent = mensagem;
  node.style.color = cores[tom] || cores.secondary;
}

async function assinarRelatorio(botao, componente) {
  const reportId = botao.getAttribute("data-report-id");
  const documentHash = botao.getAttribute("data-document-hash");

  botao.disabled = true;
  botao.textContent = "Assinando...";
  definirFeedback(botao, "Aplicando assinatura avançada...", "info");

  // 1. Assinatura criptográfica (report/start + PIN + report/complete)
  const dadosAssinatura = await componente.signUploadedReport(
    reportId,
    documentHash,
  );

  // 2. Baixar o PDF original (proxy same-origin para evitar CORS)
  definirFeedback(botao, "Gerando PDF carimbado...", "info");
  const resposta = await fetch(`/relatorios/${reportId}/pdf_original`, {
    credentials: "same-origin",
  });
  if (!resposta.ok) {
    throw new Error("Não foi possível obter o PDF original para carimbar.");
  }
  const pdfBytes = await resposta.arrayBuffer();

  // 3. Carimbar a assinatura no PDF (módulo compartilhado)
  const pdfCarimbado = await window.aplicarCarimboAssinatura(
    pdfBytes,
    dadosAssinatura,
  );

  // 4. Republicar como versão assinada
  definirFeedback(botao, "Salvando relatório assinado...", "info");
  const formData = new FormData();
  formData.append(
    "pdf",
    new Blob([pdfCarimbado], { type: "application/pdf" }),
    `relatorio-assinado-${reportId}.pdf`,
  );
  formData.append("report_id", reportId);

  const uploadResp = await fetch("/upload_signed_pdf", {
    method: "POST",
    body: formData,
    credentials: "same-origin",
  });
  const uploadData = await uploadResp.json();
  if (!uploadResp.ok || uploadData.status === "error") {
    throw new Error(uploadData.message || "Falha ao salvar o PDF assinado.");
  }

  // 5. Atualizar a interface e oferecer download
  botao.textContent = "Assinado";
  const linha = botao.closest("[data-report-row]");
  const badge = linha ? linha.querySelector("[data-status-badge]") : null;
  if (badge) {
    badge.textContent = "Assinado";
    badge.className = "badge bg-success mb-2";
  }
  definirFeedback(botao, "Relatório assinado com sucesso.", "success");

  baixarBlob(
    new Blob([pdfCarimbado], { type: "application/pdf" }),
    `relatorio-assinado-${reportId}.pdf`,
  );
}

function baixarBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
