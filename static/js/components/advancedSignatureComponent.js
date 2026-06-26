class AdvancedSignatureComponent {
  constructor(config = {}) {
    this.config = {
      apiBase: "/api/components/advanced-signature",
      uploadUrl: "/upload_pdf",
      namespace: "default",
      autoPromptRegister: true,
      requireSignature: false,
      containerSelector: "#advanced-signature-component",
      statusSelector: "[data-signature-status]",
      credentialsSelector: "[data-signature-credentials]",
      registerButtonSelector: "[data-signature-register]",
      ...config,
    };

    this.algorithmName = "ECDSA";
    this.algorithmConfig = { name: this.algorithmName, namedCurve: "P-256" };
    this.signatureAlgorithm = { name: this.algorithmName, hash: "SHA-256" };
    this.pbkdf2Iterations = 250000;
    this.dbName = "advanced-signature-component";
    this.storeName = "credentials";
    this.localCredential = null;
    this.serverStatus = null;
    this.root = document.querySelector(this.config.containerSelector);
  }

  async init() {
    if (!this.root) {
      return;
    }

    this.statusNode = this.root.querySelector(this.config.statusSelector);
    this.credentialsNode = this.root.querySelector(this.config.credentialsSelector);
    this.registerButton = this.root.querySelector(this.config.registerButtonSelector);

    if (this.registerButton) {
      this.registerButton.addEventListener("click", () => {
        this.registerDevice().catch((error) => {
          console.error("Falha ao registrar credencial:", error);
          this.setStatus(error.message || "Falha ao registrar credencial.", "danger");
          alert(error.message || "Falha ao registrar credencial.");
        });
      });
    }

    await this.refreshStatus();
  }

  async refreshStatus() {
    this.localCredential = await this.loadLocalCredential();

    try {
      this.serverStatus = await this.fetchJson(`${this.config.apiBase}/status`);
    } catch (error) {
      this.setStatus("Não foi possível consultar a assinatura avançada.", "warning");
      this.renderCredentials([]);
      throw error;
    }

    const signerName = this.serverStatus.signer_name || "Técnico";
    if (this.serverStatus.has_active_credential) {
      this.setStatus(
        `Credencial avançada ativa para ${signerName}.`,
        "success",
      );
    } else {
      this.setStatus(
        `Nenhuma credencial avançada ativa para ${signerName}.`,
        "secondary",
      );
    }

    this.renderCredentials(this.serverStatus.credentials || []);
    return this.serverStatus;
  }

  async registerDevice() {
    const deviceLabel =
      window.prompt("Nome deste dispositivo para assinatura:", "Dispositivo principal") ||
      "";
    if (!deviceLabel.trim()) {
      throw new Error("Registro cancelado.");
    }

    const pin = window.prompt("Defina um PIN para proteger esta credencial:");
    if (!pin) {
      throw new Error("PIN não informado.");
    }

    this.setStatus("Registrando credencial neste dispositivo...", "info");

    const startData = await this.fetchJson(`${this.config.apiBase}/register/start`, {
      method: "POST",
      body: JSON.stringify({ device_label: deviceLabel.trim() }),
    });

    const keyPair = await window.crypto.subtle.generateKey(
      this.algorithmConfig,
      true,
      ["sign", "verify"],
    );

    const payloadBytes = this.payloadBytes(startData.payload);
    const signatureBuffer = await window.crypto.subtle.sign(
      this.signatureAlgorithm,
      keyPair.privateKey,
      payloadBytes,
    );
    const publicKeyBuffer = await window.crypto.subtle.exportKey("spki", keyPair.publicKey);
    const privateKeyBuffer = await window.crypto.subtle.exportKey("pkcs8", keyPair.privateKey);
    const privateKeyEnvelope = await this.encryptPrivateKey(privateKeyBuffer, pin);
    const credentialId = this.createCredentialId();

    await this.fetchJson(`${this.config.apiBase}/register/complete`, {
      method: "POST",
      body: JSON.stringify({
        challenge_id: startData.challenge_id,
        credential_id: credentialId,
        public_key_b64: this.bufferToBase64(publicKeyBuffer),
        signature_b64: this.bufferToBase64(signatureBuffer),
        algorithm: "ECDSA_P256_SHA256",
      }),
    });

    await this.saveLocalCredential({
      namespace: this.config.namespace,
      credentialId,
      deviceLabel: deviceLabel.trim(),
      publicKeyB64: this.bufferToBase64(publicKeyBuffer),
      privateKeyEnvelope,
      algorithm: "ECDSA_P256_SHA256",
      createdAt: Date.now(),
    });

    await this.refreshStatus();
    this.setStatus("Credencial registrada com sucesso neste dispositivo.", "success");
  }

  async processGeneratedPdf({ pdfBlob, nome, cpf, downloadFilename }) {
    const pdfFile = new File([pdfBlob], `relatorio-${Date.now()}.pdf`, {
      type: "application/pdf",
    });

    const formData = new FormData();
    formData.append("pdf", pdfFile);
    formData.append("nome", nome || "");
    formData.append("cpf", cpf || "");
    formData.append("document_type", "Relatório Técnico");

    this.setStatus("Salvando PDF e preparando assinatura...", "info");

    const uploadData = await this.fetchJson(this.config.uploadUrl, {
      method: "POST",
      body: formData,
      isJsonRequest: false,
    });

    if (!uploadData.relatorio_id || !uploadData.document_hash) {
      if (this.config.requireSignature) {
        throw new Error("Upload concluído, mas sem dados para assinatura avançada.");
      }

      this.downloadBlob(pdfBlob, downloadFilename);
      this.setStatus("PDF salvo sem assinatura avançada.", "warning");
      return uploadData;
    }

    if (!(await this.ensureCredentialReady())) {
      if (this.config.requireSignature) {
        throw new Error("A assinatura avançada é obrigatória para este documento.");
      }

      this.downloadBlob(pdfBlob, downloadFilename);
      this.setStatus("PDF salvo com assinatura pendente.", "warning");
      return uploadData;
    }

    const signatureData = await this.signUploadedReport(
      uploadData.relatorio_id,
      uploadData.document_hash,
    );
    let finalBlob = pdfBlob;
    if (typeof this.config.buildSignedPresentationBlob === "function") {
      finalBlob =
        (await this.config.buildSignedPresentationBlob({
          originalBlob: pdfBlob,
          uploadData,
          signatureData,
        })) || pdfBlob;
    }
    this.downloadBlob(finalBlob, downloadFilename);
    this.setStatus("PDF salvo e assinado com sucesso.", "success");
    return { ...uploadData, signatureData };
  }

  async signUploadedReport(reportId, expectedHash = null) {
    const credential = await this.loadLocalCredential();
    if (!credential) {
      throw new Error("Nenhuma credencial local registrada neste dispositivo.");
    }

    const startData = await this.fetchJson(`${this.config.apiBase}/report/start`, {
      method: "POST",
      body: JSON.stringify({ report_id: reportId }),
    });

    if (expectedHash && startData.document_hash !== expectedHash) {
      throw new Error("O hash do documento não confere com o esperado.");
    }

    const pin = window.prompt("Informe o PIN da assinatura avancada:");
    if (!pin) {
      throw new Error("PIN não informado.");
    }

    this.setStatus("Aplicando assinatura avançada...", "info");

    const privateKey = await this.importPrivateKeyFromEnvelope(
      credential.privateKeyEnvelope,
      pin,
    );
    const payloadBytes = this.payloadBytes(startData.payload);
    const signatureBuffer = await window.crypto.subtle.sign(
      this.signatureAlgorithm,
      privateKey,
      payloadBytes,
    );

    const completeData = await this.fetchJson(`${this.config.apiBase}/report/complete`, {
      method: "POST",
      body: JSON.stringify({
        challenge_id: startData.challenge_id,
        credential_id: credential.credentialId,
        signature_b64: this.bufferToBase64(signatureBuffer),
      }),
    });

    await this.refreshStatus();
    return completeData;
  }

  async ensureCredentialReady() {
    this.localCredential = await this.loadLocalCredential();
    if (this.localCredential) {
      return true;
    }

    if (!this.config.autoPromptRegister) {
      return false;
    }

    const shouldRegister = window.confirm(
      "Nenhuma credencial avançada foi encontrada neste dispositivo. Deseja registrar agora?",
    );
    if (!shouldRegister) {
      return false;
    }

    await this.registerDevice();
    this.localCredential = await this.loadLocalCredential();
    return Boolean(this.localCredential);
  }

  async fetchJson(url, options = {}) {
    const {
      isJsonRequest = true,
      headers = {},
      ...fetchOptions
    } = options;

    const requestHeaders = { ...headers };
    if (isJsonRequest && !requestHeaders["Content-Type"]) {
      requestHeaders["Content-Type"] = "application/json";
    }

    const response = await fetch(url, {
      credentials: "same-origin",
      ...fetchOptions,
      headers: requestHeaders,
    });
    const responseText = await response.text();
    let data;

    try {
      data = JSON.parse(responseText);
    } catch (error) {
      const htmlLike = responseText.trim().startsWith("<");
      throw new Error(
        htmlLike
          ? "O servidor retornou uma página HTML em vez de JSON. Verifique o log do Flask."
          : "Resposta inválida do servidor.",
      );
    }

    if (!response.ok || data.status === "error") {
      throw new Error(data.message || "Falha na comunicação com o servidor.");
    }

    return data;
  }

  setStatus(message, tone = "secondary") {
    if (!this.statusNode) {
      return;
    }

    this.statusNode.textContent = message;
    this.statusNode.dataset.tone = tone;
    this.statusNode.style.color = this.pickToneColor(tone);
  }

  renderCredentials(credentials) {
    if (!this.credentialsNode) {
      return;
    }

    if (!credentials.length) {
      this.credentialsNode.innerHTML =
        '<li class="text-muted">Nenhuma credencial registrada.</li>';
      return;
    }

    const localCredentialId = this.localCredential?.credentialId;
    this.credentialsNode.innerHTML = credentials
      .map((credential) => {
        const isLocal = credential.credential_id === localCredentialId;
        const suffix = isLocal ? " (este dispositivo)" : "";
        return `
          <li>
            <strong>${this.escapeHtml(credential.device_label || "Dispositivo")}</strong>${suffix}
            <br />
            <span class="text-muted">${this.escapeHtml(
              credential.fingerprint || "",
            )}</span>
          </li>
        `;
      })
      .join("");
  }

  pickToneColor(tone) {
    const colors = {
      success: "#1d7d46",
      warning: "#8a6d1f",
      danger: "#b42318",
      info: "#0d5590",
      secondary: "#5b6470",
    };
    return colors[tone] || colors.secondary;
  }

  async openDb() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, 1);
      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(request.result);
      request.onupgradeneeded = () => {
        const db = request.result;
        if (!db.objectStoreNames.contains(this.storeName)) {
          db.createObjectStore(this.storeName, { keyPath: "namespace" });
        }
      };
    });
  }

  async saveLocalCredential(record) {
    const db = await this.openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(this.storeName, "readwrite");
      tx.oncomplete = () => resolve(record);
      tx.onerror = () => reject(tx.error);
      tx.objectStore(this.storeName).put(record);
    });
  }

  async loadLocalCredential() {
    const db = await this.openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(this.storeName, "readonly");
      const request = tx.objectStore(this.storeName).get(this.config.namespace);
      request.onsuccess = () => resolve(request.result || null);
      request.onerror = () => reject(request.error);
    });
  }

  async deriveEncryptionKey(pin, saltBuffer) {
    const material = await window.crypto.subtle.importKey(
      "raw",
      new TextEncoder().encode(pin),
      "PBKDF2",
      false,
      ["deriveKey"],
    );

    return window.crypto.subtle.deriveKey(
      {
        name: "PBKDF2",
        salt: saltBuffer,
        iterations: this.pbkdf2Iterations,
        hash: "SHA-256",
      },
      material,
      { name: "AES-GCM", length: 256 },
      false,
      ["encrypt", "decrypt"],
    );
  }

  async encryptPrivateKey(privateKeyBuffer, pin) {
    const salt = window.crypto.getRandomValues(new Uint8Array(16));
    const iv = window.crypto.getRandomValues(new Uint8Array(12));
    const aesKey = await this.deriveEncryptionKey(pin, salt);
    const cipherBuffer = await window.crypto.subtle.encrypt(
      { name: "AES-GCM", iv },
      aesKey,
      privateKeyBuffer,
    );

    return {
      cipherTextB64: this.bufferToBase64(cipherBuffer),
      ivB64: this.bufferToBase64(iv.buffer),
      saltB64: this.bufferToBase64(salt.buffer),
      iterations: this.pbkdf2Iterations,
    };
  }

  async importPrivateKeyFromEnvelope(envelope, pin) {
    try {
      const salt = this.base64ToUint8Array(envelope.saltB64);
      const iv = this.base64ToUint8Array(envelope.ivB64);
      const cipherText = this.base64ToArrayBuffer(envelope.cipherTextB64);
      const aesKey = await this.deriveEncryptionKey(pin, salt);
      const privateKeyBuffer = await window.crypto.subtle.decrypt(
        { name: "AES-GCM", iv },
        aesKey,
        cipherText,
      );

      return window.crypto.subtle.importKey(
        "pkcs8",
        privateKeyBuffer,
        this.algorithmConfig,
        false,
        ["sign"],
      );
    } catch (error) {
      throw new Error("PIN inválido ou credencial corrompida.");
    }
  }

  payloadBytes(payload) {
    return new TextEncoder().encode(this.stableStringify(payload));
  }

  stableStringify(value) {
    if (Array.isArray(value)) {
      return `[${value.map((item) => this.stableStringify(item)).join(",")}]`;
    }

    if (value && typeof value === "object") {
      const keys = Object.keys(value).sort();
      const pairs = keys.map(
        (key) => `${JSON.stringify(key)}:${this.stableStringify(value[key])}`,
      );
      return `{${pairs.join(",")}}`;
    }

    return JSON.stringify(value);
  }

  createCredentialId() {
    const bytes = window.crypto.getRandomValues(new Uint8Array(18));
    return this.bufferToBase64(bytes.buffer)
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/g, "");
  }

  bufferToBase64(buffer) {
    const bytes = buffer instanceof ArrayBuffer ? new Uint8Array(buffer) : new Uint8Array(buffer.buffer || buffer);
    let binary = "";
    const chunkSize = 0x8000;
    for (let index = 0; index < bytes.length; index += chunkSize) {
      const chunk = bytes.subarray(index, index + chunkSize);
      binary += String.fromCharCode(...chunk);
    }
    return window.btoa(binary);
  }

  base64ToArrayBuffer(base64) {
    const binary = window.atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) {
      bytes[index] = binary.charCodeAt(index);
    }
    return bytes.buffer;
  }

  base64ToUint8Array(base64) {
    return new Uint8Array(this.base64ToArrayBuffer(base64));
  }

  downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }
}

window.AdvancedSignatureComponent = AdvancedSignatureComponent;
