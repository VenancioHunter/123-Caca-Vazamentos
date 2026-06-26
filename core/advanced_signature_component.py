import base64
import hashlib
import json
import secrets
import time

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from flask import Blueprint, jsonify, render_template, request, session


class AdvancedSignatureComponent:
    @classmethod
    def register_component(cls, app, db_factory, role_checker, **kwargs):
        cls(db_factory=db_factory, **kwargs).init_app(app, role_checker)

    def __init__(
        self,
        db_factory,
        report_node="relatorios",
        route_prefix="/api/components/advanced-signature",
        challenge_ttl_seconds=10 * 60,
    ):
        self.db_factory = db_factory
        self.report_node = report_node
        self.route_prefix = route_prefix.rstrip("/")
        self.challenge_ttl_seconds = challenge_ttl_seconds
        self._blueprint_registered = False

    def init_app(self, app, role_checker):
        if self._blueprint_registered:
            return

        blueprint = Blueprint(
            "advanced_signature_component",
            __name__,
            url_prefix=self.route_prefix,
        )

        tecnico_guard = role_checker(["tecnico"])
        tecnico_admin_guard = role_checker(["tecnico", "admin"])

        @blueprint.route("/status", methods=["GET"])
        @tecnico_guard
        def status():
            user_id = session.get("user")
            user_data = {}
            if user_id:
                user_data = (
                    self.db_factory().child("users").child(user_id).get().val() or {}
                )

            credentials = (
                self.db_factory()
                .child("system_components")
                .child("advanced_signature_v1")
                .child("credentials")
                .child(self._safe_key(user_id))
                .get()
                .val()
                or {}
            )

            active_credentials = []
            for _, credential_data in credentials.items():
                if credential_data.get("status") != "active":
                    continue

                active_credentials.append(
                    {
                        "credential_id": credential_data.get("credential_id"),
                        "device_label": credential_data.get("device_label"),
                        "created_at": credential_data.get("created_at"),
                        "last_used_at": credential_data.get("last_used_at"),
                        "fingerprint": credential_data.get("fingerprint"),
                    }
                )

            return jsonify(
                {
                    "status": "ok",
                    "user_id": user_id,
                    "signer_name": user_data.get("nome_relatorio")
                    or user_data.get("name")
                    or session.get("name"),
                    "has_active_credential": len(active_credentials) > 0,
                    "credentials": active_credentials,
                }
            )

        @blueprint.route("/register/start", methods=["POST"])
        @tecnico_guard
        def register_start():
            user_id = session.get("user")
            user_data = {}
            if user_id:
                user_data = (
                    self.db_factory().child("users").child(user_id).get().val() or {}
                )

            data = request.get_json() or {}
            device_label = (data.get("device_label") or "Dispositivo principal").strip()[:80]
            challenge_id = secrets.token_urlsafe(16)
            issued_at = self._now_ts()
            payload = {
                "purpose": "register_credential",
                "user_id": user_id,
                "signer_name": user_data.get("nome_relatorio")
                or user_data.get("name")
                or session.get("name"),
                "device_label": device_label,
                "challenge": secrets.token_urlsafe(32),
                "issued_at": issued_at,
            }
            challenge_record = {
                "user_id": user_id,
                "action": "register_credential",
                "challenge": payload["challenge"],
                "issued_at": issued_at,
                "expires_at": issued_at + self.challenge_ttl_seconds,
                "payload": payload,
            }

            (
                self.db_factory()
                .child("system_components")
                .child("advanced_signature_v1")
                .child("challenges")
                .child(self._safe_key(challenge_id))
                .set(challenge_record)
            )

            return jsonify(
                {
                    "status": "ok",
                    "challenge_id": challenge_id,
                    "payload": payload,
                }
            )

        @blueprint.route("/register/complete", methods=["POST"])
        @tecnico_guard
        def register_complete():
            user_id = session.get("user")
            data = request.get_json() or {}
            challenge_id = data.get("challenge_id")
            credential_id = data.get("credential_id")
            public_key_b64 = data.get("public_key_b64")
            signature_b64 = data.get("signature_b64")
            algorithm = data.get("algorithm") or "ECDSA_P256_SHA256"

            if not all([challenge_id, credential_id, public_key_b64, signature_b64]):
                return self._error("Dados incompletos para registrar credencial", 400)

            challenge_record = (
                self.db_factory()
                .child("system_components")
                .child("advanced_signature_v1")
                .child("challenges")
                .child(self._safe_key(challenge_id))
                .get()
                .val()
            )

            if not challenge_record:
                return self._error("Desafio de assinatura nao encontrado", 404)

            if (
                challenge_record.get("user_id") != user_id
                or challenge_record.get("action") != "register_credential"
            ):
                return self._error("Desafio de assinatura invalido para este usuario", 403)

            if challenge_record.get("expires_at", 0) < self._now_ts():
                (
                    self.db_factory()
                    .child("system_components")
                    .child("advanced_signature_v1")
                    .child("challenges")
                    .child(self._safe_key(challenge_id))
                    .remove()
                )
                return self._error("Desafio de assinatura expirado", 410)

            try:
                fingerprint = self._verify_signature(
                    public_key_b64,
                    signature_b64,
                    challenge_record["payload"],
                )
            except (ValueError, InvalidSignature) as exc:
                return self._error(
                    "Assinatura de prova da credencial invalida",
                    400,
                    details=str(exc),
                )

            (
                self.db_factory()
                .child("system_components")
                .child("advanced_signature_v1")
                .child("credentials")
                .child(self._safe_key(user_id))
                .child(self._safe_key(credential_id))
                .set(
                    {
                        "credential_id": credential_id,
                        "public_key_b64": public_key_b64,
                        "algorithm": algorithm,
                        "device_label": challenge_record["payload"].get("device_label"),
                        "fingerprint": fingerprint,
                        "created_at": self._now_ts(),
                        "last_used_at": None,
                        "status": "active",
                    }
                )
            )

            (
                self.db_factory()
                .child("system_components")
                .child("advanced_signature_v1")
                .child("challenges")
                .child(self._safe_key(challenge_id))
                .remove()
            )

            return jsonify(
                {
                    "status": "ok",
                    "credential_id": credential_id,
                    "fingerprint": fingerprint,
                }
            )

        @blueprint.route("/report/start", methods=["POST"])
        @tecnico_guard
        def report_start():
            user_id = session.get("user")
            user_data = {}
            if user_id:
                user_data = (
                    self.db_factory().child("users").child(user_id).get().val() or {}
                )

            data = request.get_json() or {}
            report_id = data.get("report_id")

            if not report_id:
                return self._error("Relatorio nao informado", 400)

            report = (
                self.db_factory().child(self.report_node).child(report_id).get().val()
            )
            if not report:
                return self._error("Relatorio nao encontrado", 404)

            if report.get("tecnico_user_id") and report.get("tecnico_user_id") != user_id:
                return self._error("Este relatorio nao pertence ao tecnico logado", 403)

            if (
                not report.get("tecnico_user_id")
                and report.get("tecnico")
                and report.get("tecnico") != session.get("name")
            ):
                return self._error("Este relatorio nao pertence ao tecnico logado", 403)

            if not report.get("document_hash"):
                return self._error("Relatorio sem hash para assinatura", 400)

            challenge_id = secrets.token_urlsafe(16)
            issued_at = self._now_ts()
            payload = {
                "purpose": "sign_report",
                "report_id": report_id,
                "document_hash": report.get("document_hash"),
                "filename": report.get("filename"),
                "pdf_url": report.get("pdf_url"),
                "signer_name": user_data.get("nome_relatorio")
                or user_data.get("name")
                or session.get("name"),
                "challenge": secrets.token_urlsafe(32),
                "issued_at": issued_at,
            }

            (
                self.db_factory()
                .child("system_components")
                .child("advanced_signature_v1")
                .child("challenges")
                .child(self._safe_key(challenge_id))
                .set(
                    {
                        "user_id": user_id,
                        "action": "sign_report",
                        "challenge": payload["challenge"],
                        "issued_at": issued_at,
                        "expires_at": issued_at + self.challenge_ttl_seconds,
                        "payload": payload,
                    }
                )
            )

            (
                self.db_factory()
                .child("system_components")
                .child("advanced_signature_v1")
                .child("audit")
                .child(self._safe_key(report_id))
                .push(
                    {
                        "user_id": user_id,
                        "event_type": "challenge_started",
                        "details": {
                            "action": "sign_report",
                            "document_hash": report.get("document_hash"),
                        },
                        "ip": request.headers.get("X-Forwarded-For", request.remote_addr),
                        "user_agent": request.headers.get("User-Agent"),
                        "timestamp": self._now_ts(),
                    }
                )
            )

            return jsonify(
                {
                    "status": "ok",
                    "challenge_id": challenge_id,
                    "payload": payload,
                    "report_id": report_id,
                    "document_hash": report.get("document_hash"),
                }
            )

        @blueprint.route("/report/complete", methods=["POST"])
        @tecnico_guard
        def report_complete():
            user_id = session.get("user")
            user_data = {}
            if user_id:
                user_data = (
                    self.db_factory().child("users").child(user_id).get().val() or {}
                )

            data = request.get_json() or {}
            challenge_id = data.get("challenge_id")
            credential_id = data.get("credential_id")
            signature_b64 = data.get("signature_b64")

            if not all([challenge_id, credential_id, signature_b64]):
                return self._error("Dados incompletos para assinatura do relatorio", 400)

            challenge_record = (
                self.db_factory()
                .child("system_components")
                .child("advanced_signature_v1")
                .child("challenges")
                .child(self._safe_key(challenge_id))
                .get()
                .val()
            )

            if not challenge_record:
                return self._error("Desafio de assinatura nao encontrado", 404)

            if (
                challenge_record.get("user_id") != user_id
                or challenge_record.get("action") != "sign_report"
            ):
                return self._error("Desafio de assinatura invalido para este usuario", 403)

            if challenge_record.get("expires_at", 0) < self._now_ts():
                (
                    self.db_factory()
                    .child("system_components")
                    .child("advanced_signature_v1")
                    .child("challenges")
                    .child(self._safe_key(challenge_id))
                    .remove()
                )
                return self._error("Desafio de assinatura expirado", 410)

            payload = challenge_record["payload"]
            report_id = payload.get("report_id")
            report = (
                self.db_factory().child(self.report_node).child(report_id).get().val()
            )
            if not report:
                return self._error("Relatorio nao encontrado", 404)

            if report.get("document_hash") != payload.get("document_hash"):
                return self._error("Hash do relatorio nao confere com o desafio", 409)

            credential = (
                self.db_factory()
                .child("system_components")
                .child("advanced_signature_v1")
                .child("credentials")
                .child(self._safe_key(user_id))
                .child(self._safe_key(credential_id))
                .get()
                .val()
            )
            if not credential or credential.get("status") != "active":
                return self._error("Credencial nao encontrada ou inativa", 404)

            try:
                fingerprint = self._verify_signature(
                    credential["public_key_b64"],
                    signature_b64,
                    payload,
                )
            except (ValueError, InvalidSignature) as exc:
                (
                    self.db_factory()
                    .child("system_components")
                    .child("advanced_signature_v1")
                    .child("audit")
                    .child(self._safe_key(report_id))
                    .push(
                        {
                            "user_id": user_id,
                            "event_type": "signature_failed",
                            "details": {"reason": str(exc)},
                            "ip": request.headers.get("X-Forwarded-For", request.remote_addr),
                            "user_agent": request.headers.get("User-Agent"),
                            "timestamp": self._now_ts(),
                        }
                    )
                )
                return self._error("Assinatura do relatorio invalida", 400, details=str(exc))

            signed_at = self._now_ts()
            signature_record = {
                "credential_id": credential_id,
                "fingerprint": fingerprint,
                "algorithm": credential.get("algorithm"),
                "signature_b64": signature_b64,
                "payload": payload,
                "signed_at": signed_at,
                "signer_user_id": user_id,
                "signer_name": user_data.get("nome_relatorio")
                or user_data.get("name")
                or session.get("name"),
                "signer_document": user_data.get("cpf_cnpj")
                or user_data.get("cpf")
                or user_data.get("cnpj"),
                "device_label": credential.get("device_label"),
                "verification_code": report_id,
                "verification_url": f"/verificar-relatorio/{report_id}",
                "ip": request.headers.get("X-Forwarded-For", request.remote_addr),
                "user_agent": request.headers.get("User-Agent"),
            }

            (
                self.db_factory()
                .child(self.report_node)
                .child(report_id)
                .update(
                    {
                        "advanced_signature_component": signature_record,
                        "signature_status": "signed",
                        "signed_at": signed_at,
                    }
                )
            )

            (
                self.db_factory()
                .child("system_components")
                .child("advanced_signature_v1")
                .child("credentials")
                .child(self._safe_key(user_id))
                .child(self._safe_key(credential_id))
                .update({"last_used_at": signed_at})
            )

            (
                self.db_factory()
                .child("system_components")
                .child("advanced_signature_v1")
                .child("challenges")
                .child(self._safe_key(challenge_id))
                .remove()
            )

            (
                self.db_factory()
                .child("system_components")
                .child("advanced_signature_v1")
                .child("audit")
                .child(self._safe_key(report_id))
                .push(
                    {
                        "user_id": user_id,
                        "event_type": "report_signed",
                        "details": {
                            "credential_id": credential_id,
                            "fingerprint": fingerprint,
                            "document_hash": payload.get("document_hash"),
                        },
                        "ip": request.headers.get("X-Forwarded-For", request.remote_addr),
                        "user_agent": request.headers.get("User-Agent"),
                        "timestamp": self._now_ts(),
                    }
                )
            )

            return jsonify(
                {
                    "status": "ok",
                    "report_id": report_id,
                    "signed_at": signed_at,
                    "signer_name": signature_record.get("signer_name"),
                    "signer_document": signature_record.get("signer_document"),
                    "document_hash": report.get("document_hash"),
                    "fingerprint": fingerprint,
                    "credential_id": credential_id,
                    "device_label": signature_record.get("device_label"),
                    "verification_url": signature_record.get("verification_url"),
                    "verification_code": signature_record.get("verification_code"),
                    "valid": True,
                }
            )

        @blueprint.route("/report/<report_id>/verify", methods=["GET"])
        @tecnico_admin_guard
        def report_verify(report_id):
            verification_payload = self._build_verification_payload(report_id)
            if verification_payload.get("status") == "error":
                return jsonify(verification_payload), verification_payload.get("http_status", 400)
            return jsonify(verification_payload)

        @app.route("/verificar-relatorio/<report_id>", methods=["GET"])
        def public_report_verify(report_id):
            verification_payload = self._build_verification_payload(report_id)
            if verification_payload.get("status") == "error":
                return render_template(
                    "verificar_relatorio.html",
                    verification=verification_payload,
                    report_id=report_id,
                ), verification_payload.get("http_status", 400)
            return render_template(
                "verificar_relatorio.html",
                verification=verification_payload,
                report_id=report_id,
            )

        app.register_blueprint(blueprint)
        self._blueprint_registered = True

    @staticmethod
    def hash_bytes(raw_bytes):
        return hashlib.sha256(raw_bytes).hexdigest()

    def _now_ts(self):
        return int(time.time())

    def _b64std_bytes(self, value):
        padding = "=" * (-len(value) % 4)
        return base64.b64decode(value + padding)

    def _fingerprint(self, public_key_der):
        return hashlib.sha256(public_key_der).hexdigest()

    def _safe_key(self, value):
        if value is None or str(value).strip() == "":
            raise ValueError("Identificador invalido para assinatura")
        return hashlib.sha256(str(value).encode("utf-8")).hexdigest()

    def _payload_bytes(self, payload):
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")

    def _verify_signature(self, public_key_b64, signature_b64, payload):
        public_key_der = self._b64std_bytes(public_key_b64)
        signature_bytes = self._b64std_bytes(signature_b64)
        if len(signature_bytes) == 64:
            signature_bytes = encode_dss_signature(
                int.from_bytes(signature_bytes[:32], "big"),
                int.from_bytes(signature_bytes[32:], "big"),
            )
        public_key = serialization.load_der_public_key(public_key_der)
        public_key.verify(
            signature_bytes,
            self._payload_bytes(payload),
            ec.ECDSA(hashes.SHA256()),
        )
        return self._fingerprint(public_key_der)

    def _build_verification_payload(self, report_id):
        report = self.db_factory().child(self.report_node).child(report_id).get().val()
        if not report:
            return {
                "status": "error",
                "message": "Relatório não encontrado.",
                "http_status": 404,
            }

        signature_record = report.get("advanced_signature_component")
        if not signature_record:
            return {
                "status": "ok",
                "valid": False,
                "report_id": report_id,
                "message": "Relatório sem assinatura eletrônica avançada registrada.",
                "document_type": report.get("document_type") or "Relatório Técnico",
            }

        credential = (
            self.db_factory()
            .child("system_components")
            .child("advanced_signature_v1")
            .child("credentials")
            .child(self._safe_key(signature_record.get("signer_user_id")))
            .child(self._safe_key(signature_record.get("credential_id")))
            .get()
            .val()
        )

        if not credential:
            return {
                "status": "ok",
                "valid": False,
                "report_id": report_id,
                "message": "Credencial usada na assinatura não foi encontrada.",
                "document_type": report.get("document_type") or "Relatório Técnico",
            }

        try:
            fingerprint = self._verify_signature(
                credential["public_key_b64"],
                signature_record["signature_b64"],
                signature_record["payload"],
            )
            verification_valid = (
                signature_record["payload"].get("document_hash") == report.get("document_hash")
            )
            verification_message = (
                "Este documento consta como assinado eletronicamente no sistema."
                if verification_valid
                else "A integridade do documento não confere com o hash assinado."
            )
            cryptographic_message = (
                "Válido" if verification_valid else "Inválido"
            )
        except (ValueError, InvalidSignature) as exc:
            fingerprint = credential.get("fingerprint")
            verification_valid = False
            verification_message = "A assinatura eletrônica não pôde ser validada."
            cryptographic_message = f"Inválido ({str(exc)})"

        audit_events = (
            self.db_factory()
            .child("system_components")
            .child("advanced_signature_v1")
            .child("audit")
            .child(self._safe_key(report_id))
            .get()
            .val()
            or {}
        )

        signature_audit = None
        for _, audit_item in audit_events.items():
            if audit_item.get("event_type") == "report_signed":
                if signature_audit is None or audit_item.get("timestamp", 0) > signature_audit.get("timestamp", 0):
                    signature_audit = audit_item

        return {
            "status": "ok",
            "valid": verification_valid,
            "report_id": report_id,
            "document_type": report.get("document_type") or "Relatório Técnico",
            "message": verification_message,
            "cryptographic_validation": cryptographic_message,
            "document_hash": report.get("document_hash"),
            "signed_hash": signature_record["payload"].get("document_hash"),
            "fingerprint": fingerprint,
            "credential_id": signature_record.get("credential_id"),
            "signed_at": signature_record.get("signed_at"),
            "signer_name": signature_record.get("signer_name"),
            "signer_document": signature_record.get("signer_document"),
            "device_label": signature_record.get("device_label"),
            "verification_url": signature_record.get("verification_url") or f"/verificar-relatorio/{report_id}",
            "verification_code": signature_record.get("verification_code") or report_id,
            "ip": signature_record.get("ip") or (signature_audit or {}).get("ip"),
            "user_agent": signature_record.get("user_agent") or (signature_audit or {}).get("user_agent"),
        }

    def _error(self, message, status_code, **extra):
        payload = {"status": "error", "message": message}
        payload.update(extra)
        return jsonify(payload), status_code
