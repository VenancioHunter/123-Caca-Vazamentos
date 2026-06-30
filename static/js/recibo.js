function validarCamposObrigatoriosRecibo() {
    const camposObrigatorios = [
        "nome",
        "cpf",
        "endereco",
        "bairro",
        "cidade",
        "estado",
        "tecnicorecibo",
        "dataexecucaorebico",
        "horainicioexecucaorebico",
        "dataconclusaorebico",
        "horaconclusaoexecucaorebico",
    ];

    const mensagensErro = [];

    camposObrigatorios.forEach((id) => {
        const campo = document.getElementById(id);
        if (!campo || !campo.value.trim()) {
            const label = campo?.previousElementSibling?.textContent || id;
            mensagensErro.push(`O campo "${label}" está vazio.`);
        }
    });

    if (mensagensErro.length > 0) {
        alert(mensagensErro.join("\n"));
        return false;
    }

    return true;
}

function gerarAssinaturaRecibo(nome) {
    const canvas = document.createElement("canvas");
    canvas.width = 400;
    canvas.height = 100;
    const ctx = canvas.getContext("2d");

    ctx.fillStyle = "white";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.font = "italic 38px 'Great Vibes', cursive";
    ctx.fillStyle = "#0d47a1";
    ctx.fillText(nome, 10, 60);

    return canvas.toDataURL("image/png");
}

function formatarDataEHora(data, hora) {
    const [ano, mes, dia] = data.split("-");
    const dataFormatada = `${dia}/${mes}/${ano}`;

    const [horas, minutos] = hora.split(":");
    const horaFormatada = `${horas}h${minutos}`;

    return `${dataFormatada}, às ${horaFormatada}`;
}

function capturarFormasDePagamento() {
    const checkboxes = document.querySelectorAll(".forma-de-pagamento-recibo");

    const formasSelecionadas = Array.from(checkboxes)
        .filter((checkbox) => checkbox.checked)
        .map((checkbox) => checkbox.value);

    return formasSelecionadas.length > 0
        ? `Forma de pagamento: ${formasSelecionadas.join(", ")}.`
        : "Nenhuma forma de pagamento selecionada.";
}

async function carregarImagemRecibo(src) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.src = src;
        img.onload = () => resolve(img);
        img.onerror = reject;
    });
}

async function gerarReciboPDF() {
    if (!validarCamposObrigatoriosRecibo()) {
        return;
    }

    const { jsPDF } = window.jspdf;
    const pdf = new jsPDF({ compress: true });

    const nome = document.getElementById("nome").value;
    const cpf = document.getElementById("cpf").value;
    const endereco = document.getElementById("endereco").value;
    const bairro = document.getElementById("bairro").value;
    const cidade = document.getElementById("cidade").value;
    const data = document.getElementById("data").value;
    const observacao = document.getElementById("observacaorecibo").value.trim();

    const tipoDeServico = document.getElementById("tipodeservico").value;
    const dataInicio = document.getElementById("dataexecucaorebico").value;
    const horaInicio = document.getElementById("horainicioexecucaorebico").value;
    const dataFim = document.getElementById("dataconclusaorebico").value;
    const horaFim = document.getElementById("horaconclusaoexecucaorebico").value;

    const dataExecucao = formatarDataEHora(dataInicio, horaInicio);
    const dataConclusao = formatarDataEHora(dataFim, horaFim);

    const valorLocalizacao =
        document.getElementById("valorlocalizacao").value || "0,00";
    const valorReparo = document.getElementById("valorreparo").value || "0,00";
    const valorTotal =
        document.getElementById("valortotal").textContent || "0,00";
    const formasPagamento = capturarFormasDePagamento();
    const telefone = window.telefoneCidadeSelecionada || "Telefone não disponível";
    const larguraMaximaLinha = 180;

    let shapeTopImage = null;
    let shapeBottomImage = null;

    try {
        shapeTopImage = await carregarImagemRecibo("../static/img/shape_superior.png");
    } catch (e) {
        console.warn("Shape superior não carregado:", e);
    }

    try {
        shapeBottomImage = await carregarImagemRecibo("../static/img/shape_inferior.png");
    } catch (e) {
        console.warn("Shape inferior não carregado:", e);
    }

    function adicionarCabecalho() {
        if (shapeTopImage) {
            pdf.addImage(shapeTopImage, "PNG", 0, 0, 210, 55);
        }

        pdf.setFontSize(14);
        pdf.setTextColor(255, 255, 255);
        pdf.setFont("helvetica", "bold");
        pdf.text("123 Caça Vazamentos", 130, 20);
        pdf.setFont("helvetica", "normal");
        pdf.setFontSize(10);
        pdf.text("CNPJ: 41.713.002/0001-05", 130, 25);
        pdf.text(`Tel: ${telefone}`, 130, 30);
        pdf.text("E-mail: 123cacavazamentos@gmail.com", 130, 35);
        pdf.setTextColor(0, 0, 0);
    }

    function adicionarRodape() {
        if (shapeBottomImage) {
            pdf.addImage(shapeBottomImage, "PNG", 0, 285, 210, 17);
        }

        pdf.setTextColor(255, 255, 255);
        if (data) {
            const [ano, mes, dia] = data.split("-");
            const dataFormatada = `${dia}/${mes}/${ano}`;
            pdf.text(`${dataFormatada}, ${cidade}`, 140, 292);
        }
        pdf.setTextColor(0, 0, 0);
    }

    function escreverLinhas(linhas, x, yInicial, alturaLinha = 6) {
        let yAtual = yInicial;
        linhas.forEach((linha) => {
            pdf.text(linha, x, yAtual);
            yAtual += alturaLinha;
        });
        return yAtual;
    }

    async function escreverTextoPaginado(
        linhas,
        x,
        yInicial,
        tituloContinuacao = "",
        alturaLinha = 6,
        limiteInferior = 272,
        yNovaPagina = 60,
    ) {
        let yAtual = yInicial;

        for (const linha of linhas) {
            if (yAtual > limiteInferior) {
                adicionarRodape();
                pdf.addPage();
                adicionarCabecalho();
                yAtual = yNovaPagina;

                if (tituloContinuacao) {
                    pdf.setFont("helvetica", "bold");
                    pdf.text(tituloContinuacao, x, yAtual);
                    pdf.setFont("helvetica", "normal");
                    yAtual += alturaLinha + 2;
                }
            }

            pdf.text(linha, x, yAtual);
            yAtual += alturaLinha;
        }

        return yAtual;
    }

    adicionarCabecalho();

    pdf.setFont("helvetica", "normal");
    pdf.setFontSize(14);
    pdf.text(`${nome}`, 10, 55);
    pdf.setFontSize(10);
    pdf.text(`CPF/CNPJ: ${cpf}`, 10, 62);
    pdf.text(`Endereço: ${endereco}`, 10, 69);
    pdf.text(`Bairro: ${bairro}`, 10, 76);
    pdf.text(`Cidade: ${cidade}`, 10, 83);
    pdf.text(
        "-------------------------------------------------------------------------------------------------------------------------------------------------------------------",
        10,
        87,
    );
    pdf.setFont("helvetica", "bold");
    pdf.text("RECIBO DE PAGAMENTO", 76, 95);
    pdf.setFont("helvetica", "normal");

    const linhasServico = pdf.splitTextToSize(
        `Serviço realizado: ${tipoDeServico}`,
        larguraMaximaLinha,
    );
    let yAtual = escreverLinhas(linhasServico, 10, 105);

    const linhasExecucao = pdf.splitTextToSize(
        `Data de execução: ${dataExecucao}`,
        larguraMaximaLinha,
    );
    yAtual = escreverLinhas(linhasExecucao, 10, yAtual + 3);

    const linhasConclusao = pdf.splitTextToSize(
        `Data de conclusão: ${dataConclusao}`,
        larguraMaximaLinha,
    );
    yAtual = escreverLinhas(linhasConclusao, 10, yAtual + 3);

    yAtual += 6;
    pdf.text(`Valor da vistoria: R$${valorLocalizacao}`, 10, yAtual);
    yAtual += 7;
    pdf.text(`Valor do reparo: R$${valorReparo}`, 10, yAtual);
    yAtual += 7;
    pdf.setFont("helvetica", "bold");
    pdf.text(`Total: R$${valorTotal}`, 10, yAtual);
    pdf.setFont("helvetica", "normal");

    const linhasPagamento = pdf.splitTextToSize(formasPagamento, larguraMaximaLinha);
    yAtual = escreverLinhas(linhasPagamento, 10, yAtual + 12);

    pdf.setFont("helvetica", "bold");
    pdf.text("Observação:", 10, yAtual + 10);
    pdf.setFont("helvetica", "normal");

    let fimObservacao = yAtual + 17;

    if (observacao.length === 0) {
        pdf.text("Nenhuma observação", 10, fimObservacao);
        fimObservacao += 6;
    } else {
        const linhasObservacao = pdf.splitTextToSize(observacao, larguraMaximaLinha);
        fimObservacao = await escreverTextoPaginado(
            linhasObservacao,
            10,
            fimObservacao,
            "Observação (continuação):",
        );
    }

    const tecnicoInfo = window.obterTecnicoSelecionado("tecnicorecibo");
    const tecnicoNome = tecnicoInfo.nome;
    const tecnicoCNPJ = tecnicoInfo.cnpj;
    const modoAtribuir = window.relatorioSignatureMode === "atribuir";

    if (fimObservacao > 244) {
        adicionarRodape();
        pdf.addPage();
        adicionarCabecalho();
    }

    // No modo atribuir a assinatura é aplicada depois pelo técnico (carimbo avançado)
    if (!modoAtribuir) {
        const assinaturaImagem = gerarAssinaturaRecibo(tecnicoNome);
        pdf.addImage(assinaturaImagem, "PNG", 24, 266, 45, 20);
    }

    pdf.text("-----------------------------------", 24, 280);
    pdf.text(`${tecnicoNome}`, 24, 285);
    pdf.text(`CNPJ ${tecnicoCNPJ}`, 24, 290);

    adicionarRodape();

    if (modoAtribuir) {
        // Atendente: envia para o técnico assinar depois (status pendente)
        try {
            await window.enviarRelatorioParaAssinatura({
                pdfBlob: pdf.output("blob"),
                nome,
                cpf,
                documentType: "Recibo",
                tecnicoUserId: tecnicoInfo.userId,
            });
            alert("Recibo enviado para assinatura do técnico responsável.");
        } catch (err) {
            console.error("Falha ao enviar recibo:", err);
            alert(err.message || "Erro ao enviar o recibo para assinatura.");
        }
        return;
    }

    pdf.save(`Recibo_${nome}.pdf`);
}
