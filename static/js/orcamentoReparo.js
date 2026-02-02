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
      mensagensErro.push(`O campo "${campo.previousElementSibling.textContent}" está vazio.`);
    }
  });

  if (mensagensErro.length > 0) {
    alert(mensagensErro.join("\n"));
    return false;
  }

  return true;
}

// =============================
// FUNÇÃO PARA GERAR ASSINATURA MANUSCRITA
// =============================
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

  try {
    // SHAPE SUPERIOR
    const shapeTop = new Image();
    shapeTop.src = "../static/img/shape_superior.png";
    await new Promise((resolve, reject) => {
      shapeTop.onload = resolve;
      shapeTop.onerror = reject;
    });
    pdf.addImage(shapeTop, "PNG", 0, 0, 210, 55);
  } catch (e) {
    console.warn("Shape superior não carregado:", e);
  }

  // =============================
  // DADOS DO FORMULÁRIO
  // =============================
  const nome = document.getElementById("nome").value;
  const cpf = document.getElementById("cpf").value;
  const endereco = document.getElementById("endereco").value;
  const bairro = document.getElementById("bairro").value;
  const cidade = document.getElementById("cidade").value;
  const data = document.getElementById("data").value;
  const observacao = document.getElementById("observacao").value;

  // =============================
  // TELEFONES POR CIDADE
  // =============================
  /*const telefonesMap = {
            "Maceió": "(82) 92001-4853",
            "Satuba": "(82) 92001-4853",
            "Santa Luzia do Norte": "(82) 92001-4853",
            "Coqueiro Seco": "(82) 92001-4853",
            "Cadoz": "(82) 92001-4853",
            "Rio Largo": "(82) 92001-4853",
            "Marechal Deodoro": "(82) 92001-4853",
            "Santa Luzia": "(82) 92001-4853",
            "Pilar": "(82) 92001-4853",
            "Barra de São Miguel": "(82) 92001-4853",
            "Atalaia": "(82) 92001-4853",
            "Murici": "(82) 92001-4853",
            "Messias": "(82) 92001-4853",
            "Barra de Santo Antônio": "(82) 92001-4853",
            "Paripueira": "(82) 92001-4853",
            "Arapiraca": "(82) 92001-4853",


            "Salvador": "(71) 93300-1134",
            "Camaçari": "(71) 93300-1134",
            "Feira de Santana": "(75) 93300-2063",
            "Lauro de Freitas": "(71) 93300-1134",
            "Simões Filho": "(71) 93300-1134",
            "Gamboa": "(71) 93300-1134",
            "Vera Cruz": "(71) 93300-1134",
            "Itaparica": "(71) 93300-1134",
            "Mata de São João": "(71) 93300-1134",
            "Alagoinhas": "(71) 93300-1134",
            "Madre De Deus": "(71) 93300-1134",
            "Salinas das Margaridas": "(71) 93300-1134",


            "Goiânia": "(62) 93300-6961",
            "Aparecida de Goiânia": "(62) 93300-6961",
            "Senador Canedo": "(62) 93300-6961",
            "Trindade": "(62) 93300-6961",
            "Anápolis": "(62) 93300-6961",
            "Goianira": "(62) 93300-6961",
            "Rio Verde": "(62) 93300-6961",
            "Bela Vista": "(62) 93300-6961",
            "Hidrolândia": "(62) 93300-6961",
            "Nerópolis": "(62) 93300-6961",
            "Cesarina": "(62) 93300-6961",
            "Guapó": "(62) 93300-6961",
            "Aragoiânia": "(62) 93300-6961",
            "Maripotaba": "(62) 93300-6961",
            "Palmeiras": "(62) 93300-6961",

            "São Paulo": "(11) 93300-3231",
            "Osasco": "(11) 93300-3231",
            "Barueri": "(11) 93300-3231",
            "Campinas": "(19) 92001-6371",
            "Itupeva": "(19) 92001-6371",
            "Franco Da Rocha": "(19) 92001-6371",
            "Jundiaí": "(19) 92001-6371",
            "Campo Limpo Paulista": "(19) 92001-6371",
            "Louveira": "(19) 98563-4600",
            "Várzea Paulista": "(19) 92001-6371",
            "Vinhedo": "(19) 92001-6371",
            "Valinhos": "(19) 92001-6371",
            "Hortolândia": "(19) 92001-6371",
            "Paulínia": "(19) 92001-6371",
            "Itatiba": "(19) 92001-6371",
            "Indaiatuba": "(19) 92001-6371",
            "Jaguariúna": "(19) 92001-6371",
            "Sumaré": "(11) 93300-3231",
            "Diadema": "(11) 93300-3231",
            "Santo André": "(11) 93300-3231",
            "São Bernardo do Campo": "(11) 93300-3231",
            "São Caetano do Sul": "(19) 92001-6371",
            "Mauá": "(19) 92001-6371",
            "Jaguariúna": "(19) 92001-6371",
            "Nova Odessa": "(19) 92001-6371",
            "Americana": "(19) 92001-6371",
            "Atibaia": "(19) 92001-6371",
            "Guarulhos": "(11) 93300-3231",
            "Poa": "(11) 93300-3231",
            "Mogi das Cruzes": "(11) 93300-3231",
            "Itaquacetuba": "(11) 93300-3231",
            "Cajamar": "(19) 92001-6371",
            "Amparo": "(19) 92001-6371",
            "Capivari": "(19) 92001-6371",
            "Limeira": "(19) 92001-6371",
            "Sorocaba": "(11) 92015-4693",
            "Santos": "13 92003-6210",

            "Florianópolis": "(48) 93300-4291",
            "São José": "(48) 93300-4291",
            "Palhoça": "(48) 93300-4291",
            "Biguaçu": "(48) 93300-4291",

            "Porto Alegre": "(51) 92001-5474",
            "Canoas": "(51) 92001-5474",
            "Glorinha": "(51) 92001-5474",
            "Guaíba": "(51) 92001-5474",
            "Gravataí": "(51) 92001-5474",
            "Novo Hamburgo": "(51) 92001-5474",
            "Viamão": "(51) 92001-5474",
            "Esteio": "(51) 92001-5474",
            "Alvorada": "(51) 92001-5474",
            "São Leopoldo": "(51) 92001-5474",
            "Barra do Ribeiro": "(51) 92001-5474",
            "Eldorado do Sul": "(51) 92001-5474",
            
            "Curitiba": "(41) 92001-6421",
            "São José dos Pinhais": "(41) 92001-6421",
            "Pinhais": "(41) 92001-6421",
            "Araucária": "(41) 92001-6421",
            "Colombo": "(41) 92001-6421",
            "Campo Largo": "(41) 92001-6421",
            "Almirante Tamandaré": "(41) 92001-6421",

            "Belo Horizonte": "(31) 93300-6395",
            "Contagem": "(31) 93300-6395",
            "Betim": "(31) 93300-6395",
            "Sabará": "(31) 93300-6395",
            "Nova Lima": "(31) 93300-6395",
            "Santa Luzia": "(31) 93300-6395",
            "Ibirité": "(31) 93300-6395",
            "Itabirito": "(31) 93300-6395",
        };

  const telefone = telefonesMap[cidade] || "Telefone não disponível";*/

  const telefone = window.telefoneCidadeSelecionada || "Telefone não disponível";

  // =============================
  // CABEÇALHO DO CLIENTE
  // =============================
  pdf.setFont("helvetica", "normal");
  pdf.setFontSize(14);
  pdf.text(`${nome}`, 10, 55);
  pdf.setFontSize(10);
  pdf.text(`CPF/CNPJ: ${cpf}`, 10, 62);
  pdf.text(`Endereço: ${endereco}`, 10, 69);
  pdf.text(`Bairro: ${bairro}`, 10, 76);
  pdf.text(`Cidade: ${cidade}`, 10, 83);
  pdf.text(`-------------------------------------------------------------------------------------------------------------------------------------------------------------------`, 10, 87);

  // =============================
  // TÍTULO
  // =============================
  pdf.setFont("helvetica", "bold");
  pdf.setFontSize(16);
  pdf.text("ORÇAMENTO", 85, 95);
  pdf.setFont("helvetica", "normal");
  pdf.setFontSize(10);

  // =============================
  // INFORMAÇÕES DA EMPRESA
  // =============================
  pdf.setFontSize(14);
  pdf.setTextColor(255, 255, 255);
  pdf.setFont("helvetica", "bold");
  pdf.text(`123 Caça Vazamentos`, 130, 20);
  pdf.setFont("helvetica", "normal");
  pdf.setFontSize(10);
  pdf.text(`CNPJ: 41.713.002/0001-05`, 130, 25);
  pdf.text(`Tel: ${telefone}`, 130, 30);
  pdf.text(`E-mail: 123cacavazamentos@gmail.com`, 130, 35);

  pdf.setTextColor(0, 0, 0);

  // =============================
  // DESCRIÇÃO DOS SERVIÇOS
  // =============================
  const selectedTechniques = [];
  const allTechniques = {
    geofonamentoCheckbox: "Geofonamento com o geofone eletrônico",
    pressurizacaoCheckbox: "Pressurização da Rede",
    cameraTermograficaCheckbox: "Inspeção com câmera termográfica",
    sensorDeUmidadeCheckbox: "Verificação de umidade com o sensor de umidade",
  };

  pdf.setFont("helvetica", "bold");
  pdf.text("Descrição:", 10, 110);
  pdf.setFont("helvetica", "normal");

  const checkboxes = Object.keys(allTechniques);
  checkboxes.forEach((id) => {
    if (document.getElementById(id).checked) {
      selectedTechniques.push(allTechniques[id]);
    }
  });

  let techniquesText = "";

  if (selectedTechniques.length > 0) {
    const lastSelected = selectedTechniques.pop();
    let mainText = `Será realizado o serviço de vistoria na rede hidráulica utilizando a técnica de ${selectedTechniques.join(", ")}${selectedTechniques.length > 0 ? " e " : ""}${lastSelected}`;

    const unselectedTechniques = checkboxes
      .map((id) => allTechniques[id])
      .filter((tech) => !selectedTechniques.includes(tech) && tech !== lastSelected);

    if (unselectedTechniques.length > 0) {
      const lastOptional = unselectedTechniques.pop();
      mainText += `, se necessário será realizado ${unselectedTechniques.join(", ")}${unselectedTechniques.length > 0 ? " e " : ""}${lastOptional}`;
    }

    techniquesText = mainText + ".";
  } else {
    const outroServicoCheckbox = document.getElementById("outroServicoCheckbox");
    const descricaoPersonalizada = document.getElementById("descricaoPersonalizada").value.trim();

    if (outroServicoCheckbox.checked && descricaoPersonalizada) {
      techniquesText = descricaoPersonalizada;
    } else if (outroServicoCheckbox.checked && !descricaoPersonalizada) {
      techniquesText = "Outro serviço informado, mas sem descrição detalhada.";
    } else {
      techniquesText = "Nenhuma técnica foi selecionada.";
    }
  }

  pdf.setFont("helvetica", "bold");
  pdf.text("Descrição:", 10, 110);
  pdf.setFont("helvetica", "normal");
  const techniquesTextLinhas = pdf.splitTextToSize(techniquesText, 180);
  pdf.text(techniquesTextLinhas, 10, 117);

  // =============================
  // OBSERVAÇÃO
  // =============================
  pdf.setFont("helvetica", "bold");
  pdf.text("Observação:", 10, 140);
  pdf.setFont("helvetica", "normal");
  const linhasTextoObservacao = pdf.splitTextToSize(observacao || "Nenhuma observação", 180);
  pdf.text(linhasTextoObservacao, 10, 147);

  // =============================
  // ITENS DO ORÇAMENTO
  // =============================
  let posY = 174;
  let totalOrcamento = 0;

  pdf.setFillColor(13, 85, 144);
  pdf.rect(10, posY, 190, 9, "F");
  pdf.setTextColor(255, 255, 255);
  pdf.setFont("helvetica", "bold");
  pdf.text("ITENS", 15, posY + 6);
  pdf.text("VALOR (R$)", 175, posY + 6);
  pdf.setFont("helvetica", "normal");
  pdf.setTextColor(0, 0, 0);

  posY += 15;

  if (typeof itensOrcamento !== "undefined" && itensOrcamento.length > 0) {
    itensOrcamento.forEach((item) => {
  const unitario = item.valorUnit.toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  const totalItem = item.totalItem.toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  // Nome do item
  pdf.text(`${item.nome} (${item.qtd} un × R$ ${unitario})`, 15, posY);

  // Total do item
  pdf.text(`R$ ${totalItem}`, 195, posY, { align: "right" });

  posY += 7;
  totalOrcamento += item.totalItem;
});

  } else {
    pdf.text("Nenhum item adicionado ao orçamento.", 15, posY);
    posY += 7;
  }

  // LINHA FINAL
  pdf.text(`-------------------------------------------------------------------------------------------------------------------------------------------------------------------`, 10, posY);
  posY += 4;

  // TOTAL FINAL
  const totalFormatado = totalOrcamento.toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  pdf.setFont("helvetica", "bold");
  pdf.text("TOTAL", 15, posY + 1);
  pdf.text(`R$ ${totalFormatado}`, 195, posY + 1, { align: "right" });

  // =============================
  // ASSINATURA
    // =============================
   /*
  const tecnicoSelect = document.getElementById("tecnico");
  const tecnicoSelecionado = tecnicoSelect.options[tecnicoSelect.selectedIndex];
  const tecnicoNome = tecnicoSelecionado.value;
  const imagemAssinatura = tecnicoSelecionado.getAttribute("data-imagem");

  if (imagemAssinatura) {
    const imagemAssinaturaURL = `../static/img/${imagemAssinatura}`;
    const imgAssinatura = new Image();
    imgAssinatura.src = imagemAssinaturaURL;
    await new Promise((resolve, reject) => {
      imgAssinatura.onload = resolve;
      imgAssinatura.onerror = reject;
    });
    pdf.addImage(imgAssinatura, "PNG", 24, 262, 45, 20);
  }

  pdf.text(`-----------------------------------`, 24, 280);
  pdf.text(`${tecnicoNome}`, 29, 285);
  pdf.text(`Gerente Comercial`, 29, 290);*/
    
    
  const tecnicoSelect = document.getElementById("tecnico");
  const tecnicoSelecionado = tecnicoSelect.options[tecnicoSelect.selectedIndex];
  const tecnicoNome = tecnicoSelecionado.value;

  const assinaturaImagem = gerarAssinatura(tecnicoNome);
  pdf.addImage(assinaturaImagem, "PNG", 24, 266, 45, 20);

  // Criação do hash digital
  //const hash = btoa(`${nome}-${cpf}-${data}-${totalOrcamento}`).slice(0, 12).toUpperCase();

  pdf.setFont("helvetica", "normal");
  pdf.text(`-----------------------------------`, 24, 280);
  pdf.text(`${tecnicoNome}`, 29, 285);
  pdf.text(`Gerente Comercial`, 29, 290);
  //pdf.text(`ID de Verificação: CVZ-${hash}`, 24, 295);
  //pdf.text(`Verifique em: centralvazamentos.com.br/verificar/${hash}`, 24, 300);
  // SHAPE INFERIOR
  try {
    const shapeBottom = new Image();
    shapeBottom.src = "../static/img/shape_inferior.png";
    await new Promise((resolve, reject) => {
      shapeBottom.onload = resolve;
      shapeBottom.onerror = reject;
    });
    pdf.addImage(shapeBottom, "PNG", 0, 285, 210, 17);
  } catch (e) {
    console.warn("Shape inferior não carregado:", e);
  }

  pdf.setTextColor(255, 255, 255);
  if (data) {
    const [ano, mes, dia] = data.split("-");
    const dataFormatada = `${dia}/${mes}/${ano}`;
    pdf.text(`${dataFormatada}, ${cidade}`, 140, 292);
  }

  pdf.save(`Orcamento_${nome}.pdf`);
}


async function logo(pdf) {
    try {
        // Definir logo
        const logoURL = "../static/img/logo.png";
        const imgLogo = new Image();
        imgLogo.src = logoURL;

        // Esperar o carregamento da logo
        await new Promise((resolve, reject) => {
            imgLogo.onload = resolve;
            imgLogo.onerror = reject;
        });

        // Adicionar logo no PDF
        pdf.addImage(imgLogo, "PNG", 1, 1, 45, 45);
    } catch (error) {
        console.warn("Logo não carregada. Continuando sem logo.");
    }
}
