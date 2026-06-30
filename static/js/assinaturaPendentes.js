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

  // 3. Carimbar a assinatura no PDF
  const pdfCarimbado = await carimbarAssinatura(pdfBytes, dadosAssinatura);

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

async function carimbarAssinatura(pdfBytes, dados) {
  const { PDFDocument, StandardFonts, rgb, degrees } = window.PDFLib;
  const pdfDoc = await PDFDocument.load(pdfBytes);
  const font = await pdfDoc.embedFont(StandardFonts.Helvetica);
  const fontBold = await pdfDoc.embedFont(StandardFonts.HelveticaBold);

  const azul = rgb(0.05, 0.33, 0.56);
  const cinza = rgb(0.25, 0.28, 0.32);
  const preto = rgb(0, 0, 0);

  const caminhoVerificacao =
    dados.verification_url || `/verificar-relatorio/${dados.report_id || ""}`;
  const urlVerificacao = caminhoVerificacao.startsWith("http")
    ? caminhoVerificacao
    : `${window.location.origin}${caminhoVerificacao}`;

  // Selo lateral discreto nas duas margens de cada página do conteúdo.
  // Fica fora do corpo do texto (que começa a ~10mm das bordas), sem sobrepor nada.
  const paginas = pdfDoc.getPages();
  const seloCor = rgb(0.78, 0.1, 0.12); // vermelho
  const seloSize = 7.5;
  const seloTexto = `DOCUMENTO ASSINADO DIGITALMENTE  •  ${
    dados.signer_name || "Não informado"
  }  •  Verifique em ${urlVerificacao}`;
  const comprimentoSelo = font.widthOfTextAtSize(seloTexto, seloSize);
  paginas.forEach((p) => {
    const { width: wp, height: hp } = p.getSize();
    let inicioY = (hp - comprimentoSelo) / 2;
    if (inicioY < 45) inicioY = 45; // não invadir o rodapé decorativo
    // margem esquerda
    p.drawText(seloTexto, {
      x: 13,
      y: inicioY,
      size: seloSize,
      font,
      color: seloCor,
      rotate: degrees(90),
    });
    // margem direita
    p.drawText(seloTexto, {
      x: wp - 6,
      y: inicioY,
      size: seloSize,
      font,
      color: seloCor,
      rotate: degrees(90),
    });
  });

  // Página dedicada à assinatura, com o mesmo tamanho das demais (A4)
  const ref = paginas.length ? paginas[0].getSize() : { width: 595.28, height: 841.89 };
  const width = ref.width;
  const height = ref.height;
  const page = pdfDoc.addPage([width, height]);

  // Título centralizado
  const titulo = "ASSINATURA DIGITAL AVANÇADA";
  const tamTitulo = 16;
  const larguraTitulo = fontBold.widthOfTextAtSize(titulo, tamTitulo);
  const tituloY = height - 100;
  page.drawText(titulo, {
    x: (width - larguraTitulo) / 2,
    y: tituloY,
    size: tamTitulo,
    font: fontBold,
    color: azul,
  });

  // Caixa com os dados da assinatura
  const boxX = 50;
  const boxW = width - 100;
  const boxH = 230;
  const boxTop = tituloY - 35;
  const boxY = boxTop - boxH;

  page.drawRectangle({
    x: boxX,
    y: boxY,
    width: boxW,
    height: boxH,
    borderColor: azul,
    borderWidth: 1.2,
    color: rgb(0.96, 0.98, 1),
  });

  const linhas = [
    { texto: `Signatário: ${dados.signer_name || "Não informado"}`, size: 12, cor: preto },
    {
      texto: `Documento (CPF/CNPJ): ${dados.signer_document || "Não informado"}`,
      size: 11,
      cor: preto,
    },
    { texto: `Data/hora: ${formatarData(dados.signed_at)}`, size: 11, cor: preto },
    {
      texto: `Hash do documento: ${abreviar(dados.document_hash)}`,
      size: 10,
      cor: cinza,
    },
    {
      texto: `Impressão da credencial: ${abreviar(dados.fingerprint)}`,
      size: 10,
      cor: cinza,
    },
    {
      texto: `Código de verificação: ${dados.verification_code || dados.report_id || ""}`,
      size: 10,
      cor: cinza,
    },
    { texto: `Verifique em: ${urlVerificacao}`, size: 10, cor: azul },
  ];

  let y = boxTop - 30;
  linhas.forEach((linha) => {
    page.drawText(linha.texto, {
      x: boxX + 20,
      y,
      size: linha.size,
      font,
      color: linha.cor,
    });
    y -= 27;
  });

  // Observação abaixo da caixa
  const nota =
    "Este documento foi assinado eletronicamente. Confira a validade no endereço acima.";
  page.drawText(nota, {
    x: boxX,
    y: boxY - 24,
    size: 9,
    font,
    color: cinza,
  });

  return pdfDoc.save();
}

function abreviar(valor) {
  const texto = String(valor || "").trim();
  if (!texto) return "Não informado";
  if (texto.length <= 24) return texto;
  return `${texto.slice(0, 14)}...${texto.slice(-8)}`;
}

function formatarData(timestamp) {
  if (!timestamp && timestamp !== 0) return "Não informado";
  const data = new Date(Number(timestamp) * 1000);
  if (Number.isNaN(data.getTime())) return "Não informado";
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "medium",
    timeZone: "America/Sao_Paulo",
  }).format(data);
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
