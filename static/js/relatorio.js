function validarCamposObrigatorios() {
    // IDs dos campos obrigatórios
    const camposObrigatorios = [
        "nome",
        "cpf",
        "endereco",
        "bairro", 
        "cidade",
        "estado",
        "tecnico",
        "data",
        "selectTecnico"
    ];

    // Lista de mensagens de erro para campos vazios
    const mensagensErro = [];

    // Verifica cada campo
    camposObrigatorios.forEach(id => {
        const campo = document.getElementById(id);
        if (!campo.value.trim()) {
            mensagensErro.push(`O campo "${campo.previousElementSibling.textContent}" está vazio.`);
        }
    });

    // Exibe mensagens de erro, se houver
    if (mensagensErro.length > 0) {
        alert(mensagensErro.join("\n")); // Exibe os erros em um único alerta
        return false; // Interrompe o processo
    }

    return true; // Todos os campos estão preenchidos
}

// =============================
// FUNÇÃO PARA GERAR ASSINATURA MANUSCRITA
// =============================
function gerarAssinatura(nome) {
  const canvas = document.createElement("canvas");
  canvas.width = 400;
  canvas.height = 100;
  const ctx = canvas.getContext("2d");

  // Fundo branco
  ctx.fillStyle = "white";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Fonte cursiva em azul Bic
  ctx.font = "italic 38px 'Great Vibes', cursive";
  ctx.fillStyle = "#0d47a1"; // azul de caneta Bic
  ctx.fillText(nome, 10, 60);

  return canvas.toDataURL("image/png");
}

window.telefoneCidadeSelecionada = null;

async function gerarPDF() {

    // Impede múltiplos cliques
    const btn = document.getElementById("btnGerarPDF");
    btn.disabled = true;
    btn.innerText = "Gerando PDF...";

    document.getElementById("loadingPopup").style.display = "flex";

     // Primeiro, valida os campos obrigatórios
    if (!validarCamposObrigatorios()) {
        // Reativa o botão se houver erro
        btn.disabled = false;
        btn.innerText = "Baixar como PDF";
        document.getElementById("loadingPopup").style.display = "none";
        return;
    }

    const tecnicoSelect = document.getElementById("tecnico");
    if (!tecnicoSelect.value || tecnicoSelect.value.trim() === "") {
        alert("Por favor, selecione um técnico responsável antes de gerar o relatório.");
        // Reativa o botão
        btn.disabled = false;
        btn.innerText = "Baixar como PDF";
        document.getElementById("loadingPopup").style.display = "none";
        return;
    }

    const { jsPDF } = window.jspdf;
    const pdf = new jsPDF({ compress: true });
    let nome;
    let cpf;
    /*try {
        // Definir logo
        const logoURL = "../static/img/logo.png";
        let imgLogo = new Image();
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
    }*/
    
    
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
    
    
  // Função para carregar imagens selecionadas no input e retornar um array de DataURLs
    const carregarImagensDoInput = async (inputId) => {
        const input = document.getElementById(inputId);
        const files = input.files;
        const dataUrls = [];

        for (const file of files) {
            const dataUrl = await new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = (event) => resolve(event.target.result);
                reader.onerror = reject;
                reader.readAsDataURL(file);
            });
            dataUrls.push(dataUrl);
        }
        return dataUrls;
    };

    try {
        // Carregar as imagens do input
        const imagensDataUrls = await carregarImagensDoInput("imagens");

        // Primeira página: conteúdo textual do relatório
        /*pdf.setFontSize(16);
        pdf.text("CLIENTE", 90, 45);*/

        // Exemplo de conteúdo da primeira página
        nome = document.getElementById("nome").value;
        cpf = document.getElementById("cpf").value;
        const endereco = document.getElementById("endereco").value;
        const bairro = document.getElementById("bairro").value;
        const cidade = document.getElementById("cidade").value;
        const data = document.getElementById("data").value;
        const observacao = document.getElementById("observacao").value;
        //const total = document.getElementById("total").value;
        //const formaPagamento = document.getElementById("forma-pagamento").value;
        //const empresaSolicitacao = document.getElementById("empresaSolicitacao").value;

        const detalhesFrente = document.getElementById("detalhes_frente").value.trim();
        const detalhesFundo = document.getElementById("detalhes_fundos").value.trim();
        const detalhesAreaServico = document.getElementById("detalhes_area_servico").value.trim();
        const detalhesDispensa = document.getElementById("detalhes_dispensa").value.trim();
        const detalhesCozinha = document.getElementById("detalhes_cozinha").value.trim();
        const detalhesBanheiro = document.getElementById("detalhes_banheiro").value.trim();
        const detalhesJardim = document.getElementById("detalhes_jardim").value.trim();
        const detalhesSala = document.getElementById("detalhes_sala").value.trim();

        const detalhesAreaComum = document.getElementById("detalhes_areacomum").value.trim();
        const detalhesGaragem = document.getElementById("detalhes_garagem").value.trim();
        const detalhesPiscina = document.getElementById("detalhes_piscina").value.trim();
        const detalhesRedeDeIncendio = document.getElementById("detalhes_rededeincendio").value.trim();


        const geofonamentoCheckbox = document.getElementById("geofonamentoCheckbox");
        const pressurizacaoCheckbox = document.getElementById("pressurizacaoCheckbox");
        const cameraTermograficaCheckbox = document.getElementById("cameraTermograficaCheckbox");
        const sensorDeUmidadeCheckbox = document.getElementById("sensorDeUmidadeCheckbox");
        
        

        const larguraMaximaLinha = 180; // Ajuste conforme necessário

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
        pdf.setFont("helvetica", "bold");
        pdf.text("RELATÓRIO TÉCNICO", 85, 95);
        pdf.setFont("helvetica", "normal");


        const telefone = window.telefoneCidadeSelecionada || "Telefone não disponível";
        
          // =============================
  // INFORMAÇÕES DA EMPRESA
  // =============================
  pdf.setFontSize(14);
  pdf.setTextColor(255, 255, 255);
  pdf.setFont("helvetica", "bold");
  pdf.text(`Central Vazamentos`, 130, 20);
  pdf.setFont("helvetica", "normal");
  pdf.setFontSize(10);
  pdf.text(`CNPJ: 43.973.146/0001-26`, 130, 25);
  pdf.text(`Tel: ${telefone}`, 130, 30);
  pdf.text(`E-mail: comercial@centralvazamentos.com.br`, 130, 35);

  pdf.setTextColor(0, 0, 0);



        const selectedTechniques = [];

        // Verifica os checkboxes e adiciona os textos ao array
        if (geofonamentoCheckbox.checked) {
            selectedTechniques.push("Geofonamento com o geofone eletrônico");
        }
        if (pressurizacaoCheckbox.checked) {
            selectedTechniques.push("Pressurização da Rede");
        }
        if (cameraTermograficaCheckbox.checked) {
            selectedTechniques.push("Inspeção com câmera termográfica");
        }
        if (sensorDeUmidadeCheckbox.checked) {
            selectedTechniques.push("Verificação de umidade com o sensor de umidade");
        }

        let solicitacaoUM = true;
        let solicitacaoDois = true;

        // Formata o texto final de forma dinâmica
        let techniquesText = "";
        if (selectedTechniques.length > 0) {
            const lastTechnique = selectedTechniques.pop(); // Remove o último elemento
            techniquesText = `Técnicas utilizadas: ${selectedTechniques.join(", ")}${selectedTechniques.length > 0 ? " e " : ""}${lastTechnique}.`;

            const techniquesTextLinhas = pdf.splitTextToSize(techniquesText, larguraMaximaLinha);
            pdf.text(techniquesTextLinhas, 10, 105);
        } else {
            techniquesText = "Nenhuma técnica foi selecionada.";
        }
     
        
        // Função para formatar os itens
        function formatarLocalizacao(nome, valor) {
            if (valor) {
                return `(X) ${nome}: ${valor}`;
            } else {
                return `() ${nome}:`;
            }
        }


        const larguraLinhaLocalVazamento = 80;

        let verifica_detalhes_existe = false;

        // Construção do texto
        const locaisDireita = [
            formatarLocalizacao("Frente do imóvel", detalhesFrente),
            formatarLocalizacao("Fundos do imóvel", detalhesFundo),
            formatarLocalizacao("Área de Serviço", detalhesAreaServico),
            formatarLocalizacao("Dispensa", detalhesDispensa),
            formatarLocalizacao("Cozinha", detalhesCozinha),
            formatarLocalizacao("Banheiro", detalhesBanheiro),
        ];
        const locaisEsquerda = [
            formatarLocalizacao("Sala", detalhesSala),
            formatarLocalizacao("Jardim", detalhesJardim),
            formatarLocalizacao("Garagem", detalhesGaragem),
            formatarLocalizacao("Piscina", detalhesPiscina),
            formatarLocalizacao("Área Comum", detalhesAreaComum),
            formatarLocalizacao("Rede de Incêndio", detalhesRedeDeIncendio),
        ];

        // Adicionar título e itens ao PDF apenas se houver pelo menos um preenchido
        if (locaisDireita.some(texto => texto.includes("(X)")) || locaisEsquerda.some(texto => texto.includes("(X)"))) {
            pdf.setFont("helvetica", "bold");
            pdf.text("LOCAL DO VAZAMENTO", 85, 140);
            pdf.setFont("helvetica", "normal");

            let posicaoY = 150; // Posição inicial Y
            locaisDireita.forEach((local) => {
                pdf.text( pdf.splitTextToSize(local, larguraLinhaLocalVazamento), 20, posicaoY); // Escreve cada item no PDF
                posicaoY += 12; // Incrementa a posição Y
            });

            let posicaoYD = 150; // Posição inicial Y
            locaisEsquerda.forEach((local) => {
                pdf.text(pdf.splitTextToSize(local, larguraLinhaLocalVazamento), 110, posicaoYD); // Escreve cada item no PDF
                posicaoYD += 12; // Incrementa a posição Y
            });
            verifica_detalhes_existe = true;
        }
        
        
        // OBSERVAÇÃO
        const linhasTextoObservacao = pdf.splitTextToSize(observacao, larguraMaximaLinha);
        

        if (verifica_detalhes_existe == true) {
            pdf.setFont("helvetica", "bold"); 
            pdf.text("Observação:", 10, 220);
            pdf.setFont("helvetica", "normal");

            if (observacao.length === 0) {
            pdf.text(`Nenhuma observação`, 10, 227);
            }
            else {
                pdf.text(linhasTextoObservacao, 10, 227);
            }
        }
        else {
            pdf.setFont("helvetica", "bold"); 
            pdf.text("Observação:", 10, 140);
            pdf.setFont("helvetica", "normal");

            if (observacao.length === 0) {
            pdf.text(`Nenhuma observação`, 10, 147);
            }
            else {
                pdf.text(linhasTextoObservacao, 10, 147);
            }
        }
        
        
        /*pdf.text(`-------------------------------------------------------------------------------------------------------------------------------------------------------------------`, 10, 240);


        // SOLICITAÇÃO
        let solicitacao = '';
        
        if (empresaSolicitacao !== 'selecionar') {
            
            if (solicitacaoUM == true || solicitacaoDois == true) {
                solicitacao = `Por meio desse relatório, solicitamos à ${empresaSolicitacao}, a refazer as contas altas.`;
            }
            else {
                solicitacao = `Por meio desse relatório, solicitamos à ${empresaSolicitacao} a refazer as contas altas já que essa água não foi consumida e sim perdida no solo, sem o conhecimento e a intenção do cliente.`;
            }

            const linhasTextoSolicitacaoEmpresa = pdf.splitTextToSize(solicitacao, larguraMaximaLinha);
            pdf.setFont("helvetica", "bold"); 
            pdf.text("SOLICITAÇÃO", 90, 245);
            pdf.setFont("helvetica", "normal");
            pdf.text(linhasTextoSolicitacaoEmpresa, 10, 253);
     
        };*/
        //const garantiaUm = `Garantia total no local localizado pelo técnico. ( Prazo máximo de 30 dias para acionar a garantia) caso solicite a mesma sem a necessidade devida, será cobrado novamente o valor do serviço de localização.`;
        //const linhasTextoGaramtiaUm = pdf.splitTextToSize( garantiaUm, larguraMaximaLinha);
        //pdf.text(linhasTextoGaramtiaUm, 10, 245);

        //const garantiaDois = `Garantia de 180 dias em todos os serviços  hidráulicos reparados pela empresa. Porém se o reparo for executado por terceiros, prevalece a garantia de 30 dias da localização.`;
        //const linhasTextoGaramtiaDois = pdf.splitTextToSize( garantiaDois, larguraMaximaLinha);
        //pdf.text(linhasTextoGaramtiaDois, 10, 255);

        // Obter o técnico selecionado e o CNPJ
        const selectTecnico = document.getElementById('tecnico');
        const tecnicoSelecionado = selectTecnico.options[selectTecnico.selectedIndex];
        const tecnicoNome = tecnicoSelecionado.value; // Nome do técnico
        const tecnicoCNPJ = tecnicoSelecionado.getAttribute('data-cnpj'); // CNPJ do técnico
        const imagemAssinatura = tecnicoSelecionado.getAttribute('data-imagem');
        /*
        if (imagemAssinatura) {
            const imagemAssinaturaURL = `../static/img/${imagemAssinatura}`;
            const imgAssinatura = new Image();
            imgAssinatura.src = imagemAssinaturaURL;

            // Esperar o carregamento da imagem
            await new Promise((resolve, reject) => {
                imgAssinatura.onload = resolve;
                imgAssinatura.onerror = reject;
            });

            // Adicionar a assinatura no PDF
            pdf.addImage(imgAssinatura, "PNG", 15, 262, 45, 20); // Ajuste as dimensões conforme necessário
        }*/

        const assinaturaImagem = gerarAssinatura(tecnicoNome);
        pdf.addImage(assinaturaImagem, "PNG", 24, 266, 45, 20);
        // Adicionar informações do técnico
        pdf.text(`-----------------------------------`, 24, 280);    
        pdf.text(`${tecnicoNome}`, 24, 285);
        pdf.text(`CNPJ ${tecnicoCNPJ}`, 24, 290);



        
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
        pdf.setTextColor(0, 0, 0);

        // -----------------------------------------------------------------------------------------------------------

        

        const tipoDeVistoria = document.getElementById("tipodeservicoVistoria").value;

        let textUM = '';
        let textDois = '';
        

        const possuiVazamento = document.querySelector('input[name="possui-vazamento"]:checked')?.value;
        const revisarConta = document.querySelector('input[name="revisar-conta"]:checked')?.value;

        if (tipoDeVistoria === 'Conta Alta') {
            // ||    
            if (possuiVazamento === "sim" && revisarConta === "sim") {
                pdf.addPage();

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
                // INFORMAÇÕES DA EMPRESA
                // =============================
                pdf.setFontSize(14);
                pdf.setTextColor(255, 255, 255);
                pdf.setFont("helvetica", "bold");
                pdf.text(`Central Vazamentos`, 130, 20);
                pdf.setFont("helvetica", "normal");
                pdf.setFontSize(10);
                pdf.text(`CNPJ: 43.973.146/0001-26`, 130, 25);
                pdf.text(`Tel: ${telefone}`, 130, 30);
                pdf.text(`E-mail: comercial@centralvazamentos.com.br`, 130, 35);

                pdf.setTextColor(0, 0, 0);

                //await logo(pdf);
                textUM = 'No local identificado não havia evidências superficiais de vazamento, de modo que não havia possibilidade de o cliente identificar a existência do vazamento no local sem os serviços técnicos contratados.'
                textDois = 'As características acima indicadas podem ensejar a revisão das contas de água e de esgoto junto à Concessionária do Serviço Público de Saneamento Básico, a qual deverá ser instruída com este Laudo Técnico.';
                const P1 = pdf.splitTextToSize(textUM, larguraMaximaLinha);
                const P2 = pdf.splitTextToSize(textDois, larguraMaximaLinha);
                pdf.setFont("helvetica", "bold"); 
                pdf.text("SOLICITAÇÃO", 90, 70);
                pdf.setFont("helvetica", "normal");
                pdf.text(P1, 10, 80);
                pdf.text(P2, 10, 90);

                /*if (imagemAssinatura) {
                    const imagemAssinaturaURL = `../static/img/${imagemAssinatura}`;
                    const imgAssinatura = new Image();
                    imgAssinatura.src = imagemAssinaturaURL;

                    // Esperar o carregamento da imagem
                    await new Promise((resolve, reject) => {
                        imgAssinatura.onload = resolve;
                        imgAssinatura.onerror = reject;
                    });

                    // Adicionar a assinatura no PDF
                    pdf.addImage(imgAssinatura, "PNG", 15, 262, 45, 20); // Ajuste as dimensões conforme necessário
                }
                // Adicionar informações do técnico
                pdf.text(`-----------------------------------`, 15, 280);    
                pdf.text(`${tecnicoNome}`, 15, 285);
                pdf.text(`CNPJ ${tecnicoCNPJ}`, 15, 290);*/

                const assinaturaImagem = gerarAssinatura(tecnicoNome);
                pdf.addImage(assinaturaImagem, "PNG", 24, 266, 45, 20);
                // Adicionar informações do técnico
                pdf.text(`-----------------------------------`, 24, 280);    
                pdf.text(`${tecnicoNome}`, 24, 285);
                pdf.text(`CNPJ ${tecnicoCNPJ}`, 24, 290);

            }
            else if (possuiVazamento === "nao" && revisarConta === "sim") {
                pdf.addPage();

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
                // INFORMAÇÕES DA EMPRESA
                // =============================
                pdf.setFontSize(14);
                pdf.setTextColor(255, 255, 255);
                pdf.setFont("helvetica", "bold");
                pdf.text(`Central Vazamentos`, 130, 20);
                pdf.setFont("helvetica", "normal");
                pdf.setFontSize(10);
                pdf.text(`CNPJ: 43.973.146/0001-26`, 130, 25);
                pdf.text(`Tel: ${telefone}`, 130, 30);
                pdf.text(`E-mail: comercial@centralvazamentos.com.br`, 130, 35);

                pdf.setTextColor(0, 0, 0);

                //await logo(pdf);
                textUM = 'Após a inspeção técnica no local, não foram identificadas evidências superficiais ou ocultas de vazamento, de modo que a área analisada não apresentou quaisquer sinais de perda de água ou problemas relacionados.'
                textDois = 'As características acima indicadas podem ensejar a revisão das contas de água e de esgoto junto à Concessionária do Serviço Público de Saneamento Básico, a qual deverá ser instruída com este Relatório Técnico.';
                const P1 = pdf.splitTextToSize(textUM, larguraMaximaLinha);
                const P2 = pdf.splitTextToSize(textDois, larguraMaximaLinha);
                pdf.setFont("helvetica", "bold"); 
                pdf.text("SOLICITAÇÃO", 90, 70);
                pdf.setFont("helvetica", "normal");
                pdf.text(P1, 10, 80);
                pdf.text(P2, 10, 90);

                /*if (imagemAssinatura) {
                    const imagemAssinaturaURL = `../static/img/${imagemAssinatura}`;
                    const imgAssinatura = new Image();
                    imgAssinatura.src = imagemAssinaturaURL;

                    // Esperar o carregamento da imagem
                    await new Promise((resolve, reject) => {
                        imgAssinatura.onload = resolve;
                        imgAssinatura.onerror = reject;
                    });

                    // Adicionar a assinatura no PDF
                    pdf.addImage(imgAssinatura, "PNG", 15, 262, 45, 20); // Ajuste as dimensões conforme necessário
                }
                // Adicionar informações do técnico
                pdf.text(`-----------------------------------`, 15, 280);    
                pdf.text(`${tecnicoNome}`, 15, 285);
                pdf.text(`CNPJ ${tecnicoCNPJ}`, 15, 290);*/

                const assinaturaImagem = gerarAssinatura(tecnicoNome);
                pdf.addImage(assinaturaImagem, "PNG", 24, 266, 45, 20);
                // Adicionar informações do técnico
                pdf.text(`-----------------------------------`, 24, 280);    
                pdf.text(`${tecnicoNome}`, 24, 285);
                pdf.text(`CNPJ ${tecnicoCNPJ}`, 24, 290);


            }
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
                pdf.setTextColor(0, 0, 0);
        };

        // ------------------------------------------------------------------------------------------------------------


        // Adicionar uma nova página para começar a inserir as imagens
        if (imagensDataUrls.length != 0){
        pdf.addPage();

        pdf.setFont("helvetica", "bold");
        pdf.text("ANEXO", 95, 10);
        pdf.setFont("helvetica", "normal");
        // Configura a posição inicial na segunda página
        // Configura a posição inicial na segunda página
        // Configura a posição inicial na segunda página
        let yPosition = 22;
        let positionAnexo = 20;
        let countAnexo = 1;

        // Adicionar cada imagem a partir da segunda página
        for (const dataUrl of imagensDataUrls) {
            const imgComprimida = await comprimirImagem(dataUrl, 0.7); // 70% de qualidade (ótimo equilíbrio)

            const img = new Image();
            img.src = imgComprimida;
            await new Promise((resolve, reject) => {
                img.onload = resolve;
                img.onerror = reject;
            });

            const imgWidth = img.naturalWidth;
            const imgHeight = img.naturalHeight;

            const maxWidth = 150;
            const maxHeight = 100;
            let width = imgWidth;
            let height = imgHeight;

            if (imgWidth > maxWidth || imgHeight > maxHeight) {
                const widthRatio = maxWidth / imgWidth;
                const heightRatio = maxHeight / imgHeight;
                const scale = Math.min(widthRatio, heightRatio);
                width = imgWidth * scale;
                height = imgHeight * scale;
            }

            if (yPosition + height > 280) {
                pdf.addPage();
                yPosition = 22;
                positionAnexo = 20;
            }

            pdf.text(`Imagem: ${countAnexo}`, 10, positionAnexo);
            pdf.addImage(imgComprimida, "JPEG", 10, yPosition, width, height);

            yPosition += height + 10;
            positionAnexo = yPosition - 5;
            countAnexo += 1;
            }
        }

    } catch (error) {
        console.warn("Erro ao carregar uma ou mais imagens:", error);
    }

    // Salvar PDF
    // Primeiro gera o blob
    // MOSTRA POP-UP
document.getElementById("loadingPopup").style.display = "flex";
/*
// Primeiro gera o blob antes de salvar
const pdfBlob = pdf.output("blob");

// Converte para File (compatível com celulares)
const pdfFile = new File([pdfBlob], `relatorio-${Date.now()}.pdf`, {
    type: "application/pdf"
});



// Monta o formData
const formData = new FormData();
formData.append("pdf", pdfFile);
formData.append("nome", nome);
formData.append("cpf", cpf);

// Envia para o servidor
fetch("/upload_pdf", {
    method: "POST",
    body: formData
})
.then(res => res.json())
.then(data => {
    console.log("Upload OK:", data);

    // Depois do upload → baixa o PDF
    pdf.save(`Relatorio_Tecnico_${nome}.pdf`);

    // Depois de tudo → fecha popup e ativa botão
    setTimeout(() => {
        document.getElementById("loadingPopup").style.display = "none";
        btn.disabled = false;
        btn.innerText = "Baixar como PDF";
    }, 1200);
})
.catch(err => {
    console.error("Falha no upload:", err);
    alert("Erro ao enviar o relatório. Verifique sua conexão.");

    // Libera botão e popup mesmo se der erro
    document.getElementById("loadingPopup").style.display = "none";
    btn.disabled = false;
    btn.innerText = "Baixar como PDF";
});*/
pdf.save(`Relatorio_Tecnico_${nome}.pdf`);
document.getElementById("loadingPopup").style.display = "none";
btn.disabled = false;
btn.innerText = "Baixar como PDF";
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

async function comprimirImagem(dataUrl, qualidade = 0.7) {
  return new Promise((resolve) => {
    const img = new Image();
    img.src = dataUrl;
    img.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = img.width;
      canvas.height = img.height;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      resolve(canvas.toDataURL("image/jpeg", qualidade)); // converte e comprime
    };
  });
}

