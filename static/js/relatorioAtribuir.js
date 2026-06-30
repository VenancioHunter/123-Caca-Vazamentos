// =============================================================
// Modo "atribuir": o atendente monta o relatório e atribui a um
// técnico para assinar depois com a assinatura digital avançada.
// =============================================================

// Lê o técnico selecionado de forma uniforme nos dois modos:
// - modo "atribuir": option.value = UID do técnico, com data-nome/data-cnpj
// - demais modos: option.value = nome do técnico (comportamento antigo)
window.obterTecnicoSelecionado = function (selectId) {
  const select = document.getElementById(selectId);
  if (!select || select.selectedIndex < 0) {
    return { userId: "", nome: "", cnpj: "" };
  }

  const opt = select.options[select.selectedIndex];
  const atribuir = window.relatorioSignatureMode === "atribuir";

  return {
    userId: atribuir ? opt.value : opt.getAttribute("data-uid") || "",
    nome: atribuir
      ? opt.getAttribute("data-nome") || opt.text.trim()
      : opt.value,
    cnpj: opt.getAttribute("data-cnpj") || "",
  };
};

// Sobe o PDF gerado para o backend já atribuído a um técnico (status pendente).
window.enviarRelatorioParaAssinatura = async function ({
  pdfBlob,
  nome,
  cpf,
  documentType,
  tecnicoUserId,
}) {
  if (!tecnicoUserId) {
    throw new Error("Selecione um técnico responsável antes de enviar.");
  }

  const pdfFile = new File([pdfBlob], `relatorio-${Date.now()}.pdf`, {
    type: "application/pdf",
  });

  const formData = new FormData();
  formData.append("pdf", pdfFile);
  formData.append("nome", nome || "");
  formData.append("cpf", cpf || "");
  formData.append("document_type", documentType || "Relatório Técnico");
  formData.append("tecnico_user_id", tecnicoUserId);

  const response = await fetch("/upload_pdf", {
    method: "POST",
    body: formData,
    credentials: "same-origin",
  });

  const texto = await response.text();
  let data;
  try {
    data = JSON.parse(texto);
  } catch (e) {
    throw new Error("Resposta inválida do servidor ao enviar o relatório.");
  }

  if (!response.ok || data.status === "error") {
    throw new Error(data.message || "Falha ao enviar o relatório.");
  }

  return data;
};
