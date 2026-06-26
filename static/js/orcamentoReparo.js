function validarCamposObrigatorios() {
  const camposObrigatorios = [
    "nome",
    "cpf",
    "endereco",
    "bairro",
    "cidade",
    "estado",
    "tecnico",
    "data",
  ];

  const mensagensErro = [];

  camposObrigatorios.forEach((id) => {
    const campo = document.getElementById(id);
    if (!campo.value.trim()) {
      mensagensErro.push(
        `O campo "${campo.previousElementSibling.textContent}" está vazio.`,
      );
    }
  });

  if (mensagensErro.length > 0) {
    alert(mensagensErro.join("\n"));
    return false;
  }

  return true;
}

function gerarAssinatura(nome) {
  const canvas = document.createElement("canvas");
  canvas.width = 400;
  canvas.height = 100;
  const ctx = canvas.getContext("2d");

  ctx.fillStyle = "white";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.font = "italic 38px 'Great Vibes', cursive";
  ctx.fillStyle = "#000";
  ctx.fillText(nome, 10, 60);

  return canvas.toDataURL("image/png");
}

window.telefoneCidadeSelecionada = null;

async function gerarPDF() {
  if (!validarCamposObrigatorios()) return;

  const { jsPDF } = window.jspdf;
  const pdf = new jsPDF();

  const nome = document.getElementById("nome").value;
  const cpf = document.getElementById("cpf").value;
  const endereco = document.getElementById("endereco").value;
  const bairro = document.getElementById("bairro").value;
  const cidade = document.getElementById("cidade").value;
  const data = document.getElementById("data").value;
  const observacao = document.getElementById("observacao").value;
  const telefone = window.telefoneCidadeSelecionada || "Telefone não disponível";

  const LIMITE_CONTEUDO_Y = 248;
  const POSICAO_CONTINUACAO_Y = 45;
  const ALTURA_LINHA = 6;

  async function adicionarShapeSuperiorPagina() {
    try {
      const shapeTop = new Image();
      shapeTop.src = "../static/img/shape_123_superior.png";
      await new Promise((resolve, reject) => {
        shapeTop.onload = resolve;
        shapeTop.onerror = reject;
      });
      pdf.addImage(shapeTop, "PNG", 0, 0, 210, 33);
    } catch (e) {
      console.warn("Shape superior não carregado:", e);
    }
  }

  async function adicionarRodapePagina() {
    try {
      const shapeBottom = new Image();
      shapeBottom.src = "../static/img/shape_123_inferior.png";
      await new Promise((resolve, reject) => {
        shapeBottom.onload = resolve;
        shapeBottom.onerror = reject;
      });
      pdf.addImage(shapeBottom, "PNG", 0, 282, 210, 17);
    } catch (e) {
      console.warn("Shape inferior não carregado:", e);
    }

    pdf.setTextColor(255, 255, 255);
    if (data) {
      const [ano, mes, dia] = data.split("-");
      const dataFormatada = `${dia}/${mes}/${ano}`;
      pdf.text(`${dataFormatada}, ${cidade}`, 140, 292);
    }
    pdf.setTextColor(0, 0, 0);
  }

  async function abrirNovaPagina() {
    await adicionarRodapePagina();
    pdf.addPage();
    await adicionarShapeSuperiorPagina();
    pdf.setFont("helvetica", "normal");
    pdf.setFontSize(10);
    pdf.setTextColor(0, 0, 0);
    return POSICAO_CONTINUACAO_Y;
  }

  async function escreverBlocoTexto(titulo, texto, posY, espacamentoFinal = 10) {
    const linhas = pdf.splitTextToSize(texto, 180);
    let tituloAtual = titulo;

    pdf.setFont("helvetica", "bold");
    pdf.setTextColor(6, 32, 58);
    pdf.text(tituloAtual, 10, posY);
    pdf.setFont("helvetica", "normal");
    pdf.setTextColor(0, 0, 0);
    posY += 7;

    for (const linha of linhas) {
      if (posY > LIMITE_CONTEUDO_Y) {
        posY = await abrirNovaPagina();
        tituloAtual = `${titulo} (continuação):`;
        pdf.setFont("helvetica", "bold");
        pdf.setTextColor(6, 32, 58);
        pdf.text(tituloAtual, 10, posY);
        pdf.setFont("helvetica", "normal");
        pdf.setTextColor(0, 0, 0);
        posY += 7;
      }

      pdf.text(linha, 10, posY);
      posY += ALTURA_LINHA;
    }

    return posY + espacamentoFinal;
  }

  function desenharCabecalhoItens(posY) {
    pdf.setFillColor(6, 32, 58);
    pdf.rect(10, posY, 150, 9, "F");
    pdf.setFillColor(147, 205, 228);
    pdf.rect(160, posY, 40, 9, "F");
    pdf.setTextColor(255, 255, 255);
    pdf.setFont("helvetica", "bold");
    pdf.text("ITENS", 15, posY + 6);
    pdf.text("VALOR (R$)", 175, posY + 6);
    pdf.setFont("helvetica", "normal");
    pdf.setTextColor(0, 0, 0);
  }

  await adicionarShapeSuperiorPagina();

  pdf.setFont("helvetica", "normal");
  pdf.setFontSize(14);
  pdf.setTextColor(6, 32, 58);
  pdf.text(`${nome}`, 10, 55);
  pdf.setTextColor(0, 0, 0);
  pdf.setFontSize(10);
  pdf.text(`CPF/CNPJ: ${cpf}`, 10, 62);
  pdf.text(`Endereço: ${endereco}`, 10, 67);
  pdf.text(`Bairro: ${bairro}`, 10, 72);
  pdf.text(`Cidade: ${cidade}`, 10, 77);

  pdf.setFont("helvetica", "bold");
  pdf.setFontSize(16);
  pdf.setTextColor(6, 32, 58);
  pdf.text("ORÇAMENTO", 85, 95);
  pdf.setFont("helvetica", "normal");
  pdf.setFontSize(10);
  pdf.setTextColor(0, 0, 0);

  pdf.setFontSize(10);
  pdf.setTextColor(6, 32, 58);
  pdf.text("CNPJ: 41.713.002/0001-05", 130, 8);
  pdf.text(`Telefone: ${telefone}`, 130, 13);
  pdf.text("E-mail: 123cacavazamentos@gmail.com", 130, 18);
  pdf.setTextColor(0, 0, 0);

  const selectedTechniques = [];
  const allTechniques = {
    geofonamentoCheckbox: "Geofonamento com o geofone eletrônico",
    pressurizacaoCheckbox: "Pressurização da Rede",
    cameraTermograficaCheckbox: "Inspeção com câmera termográfica",
    sensorDeUmidadeCheckbox: "Verificação de umidade com o sensor de umidade",
  };

  const checkboxes = Object.keys(allTechniques);
  checkboxes.forEach((id) => {
    if (document.getElementById(id).checked) {
      selectedTechniques.push(allTechniques[id]);
    }
  });

  let techniquesText = "";

  if (selectedTechniques.length > 0) {
    const tecnicasSelecionadas = [...selectedTechniques];
    const ultimaSelecionada = tecnicasSelecionadas.pop();
    let textoPrincipal =
      `Será realizado o serviço de vistoria na rede hidráulica utilizando a técnica de ` +
      `${tecnicasSelecionadas.join(", ")}` +
      `${tecnicasSelecionadas.length > 0 ? " e " : ""}${ultimaSelecionada}`;

    const tecnicasNaoSelecionadas = checkboxes
      .map((id) => allTechniques[id])
      .filter((tech) => !selectedTechniques.includes(tech));

    if (tecnicasNaoSelecionadas.length > 0) {
      const tecnicasOpcionais = [...tecnicasNaoSelecionadas];
      const ultimaOpcional = tecnicasOpcionais.pop();
      textoPrincipal +=
        `, se necessário será realizado ` +
        `${tecnicasOpcionais.join(", ")}` +
        `${tecnicasOpcionais.length > 0 ? " e " : ""}${ultimaOpcional}`;
    }

    techniquesText = `${textoPrincipal}.`;
  } else {
    const outroServicoCheckbox = document.getElementById("outroServicoCheckbox");
    const descricaoPersonalizada = document
      .getElementById("descricaoPersonalizada")
      .value.trim();

    if (outroServicoCheckbox.checked && descricaoPersonalizada) {
      techniquesText = descricaoPersonalizada;
    } else if (outroServicoCheckbox.checked) {
      techniquesText = "Outro serviço informado, mas sem descrição detalhada.";
    } else {
      techniquesText = "Nenhuma técnica foi selecionada.";
    }
  }

  let posY = await escreverBlocoTexto("Descrição:", techniquesText, 110, 12);

  let totalOrcamento = 0;
  if (posY + 15 > LIMITE_CONTEUDO_Y) {
    posY = await abrirNovaPagina();
  }
  desenharCabecalhoItens(posY);
  posY += 15;

  if (typeof itensOrcamento !== "undefined" && itensOrcamento.length > 0) {
    for (const item of itensOrcamento) {
      const unitario = item.valorUnit.toLocaleString("pt-BR", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });

      const totalItem = item.totalItem.toLocaleString("pt-BR", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });

      const linhasItem = pdf.splitTextToSize(
        `${item.nome} (${item.qtd} un × R$ ${unitario})`,
        140,
      );
      const alturaItem = Math.max(
        linhasItem.length * ALTURA_LINHA,
        ALTURA_LINHA,
      );

      if (posY + alturaItem > LIMITE_CONTEUDO_Y) {
        posY = await abrirNovaPagina();
        desenharCabecalhoItens(posY);
        posY += 15;
      }

      pdf.text(linhasItem, 15, posY);
      pdf.text(`R$ ${totalItem}`, 195, posY, { align: "right" });

      posY += alturaItem + 1;
      totalOrcamento += item.totalItem;
    }
  } else {
    pdf.text("Nenhum item adicionado ao orçamento.", 15, posY);
    posY += 7;
  }

  const totalFormatado = totalOrcamento.toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  if (posY + 10 > LIMITE_CONTEUDO_Y) {
    posY = await abrirNovaPagina();
  }

  pdf.setFillColor(6, 32, 58);
  pdf.rect(10, posY - 2, 190, 9, "F");
  pdf.setFont("helvetica", "bold");
  pdf.setTextColor(255, 255, 255);
  pdf.text("TOTAL", 15, posY + 4);
  pdf.text(`R$ ${totalFormatado}`, 195, posY + 4, { align: "right" });
  pdf.setTextColor(0, 0, 0);

  posY = await escreverBlocoTexto(
    "Observação:",
    observacao || "Nenhuma observação",
    posY + 16,
    8,
  );

  const tecnicoSelect = document.getElementById("tecnico");
  const tecnicoSelecionado = tecnicoSelect.options[tecnicoSelect.selectedIndex];
  const tecnicoNome = tecnicoSelecionado.value;

  if (posY > 235) {
    await abrirNovaPagina();
  }

  const assinaturaImagem = gerarAssinatura(tecnicoNome);
  pdf.addImage(assinaturaImagem, "PNG", 24, 266, 45, 20);
  pdf.setFont("helvetica", "normal");
  pdf.text("-----------------------------------", 24, 280);
  pdf.text(`${tecnicoNome}`, 29, 285);
  pdf.text("Gerente Comercial", 29, 290);

  await adicionarRodapePagina();

  pdf.save(`Orcamento_${nome}.pdf`);
}

async function logo(pdf) {
  try {
    const logoURL = "../static/img/logo.png";
    const imgLogo = new Image();
    imgLogo.src = logoURL;

    await new Promise((resolve, reject) => {
      imgLogo.onload = resolve;
      imgLogo.onerror = reject;
    });

    pdf.addImage(imgLogo, "PNG", 1, 1, 45, 45);
  } catch (error) {
    console.warn("Logo não carregada. Continuando sem logo.");
  }
}
