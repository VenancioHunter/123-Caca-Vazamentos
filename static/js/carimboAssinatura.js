// =============================================================
// Carimbo de assinatura digital avançada (pdf-lib), compartilhado
// entre o fluxo de assinatura imediata (/relatorio_tecnico) e o de
// relatórios pendentes (/relatorios_pendentes).
//
// Aplica em qualquer PDF:
//  - selos vermelhos verticais nas duas margens de cada página;
//  - uma folha de assinatura dedicada ao final do documento.
//
// Expõe: window.aplicarCarimboAssinatura(pdfBytes, dados) -> Uint8Array
// `pdfBytes` pode ser ArrayBuffer/Uint8Array; `dados` traz os campos da
// assinatura (signer_name, signer_document, signed_at, document_hash,
// fingerprint, verification_url, verification_code, report_id).
// =============================================================

(function () {
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

  window.aplicarCarimboAssinatura = async function (pdfBytes, dados) {
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
    const ref = paginas.length
      ? paginas[0].getSize()
      : { width: 595.28, height: 841.89 };
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
  };
})();
