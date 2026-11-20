(function () {
  "use strict";

  const state = {
    statusFilter: "ALL",
    defaults: null,
    selectedOrderCode: null,
    agentOrderContext: null,
  };

  function qs(selector) {
    return document.querySelector(selector);
  }

  function qsa(selector) {
    return Array.from(document.querySelectorAll(selector));
  }

  function escapeHtml(raw) {
    return String(raw ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function statusBadgeClass(status) {
    const up = String(status || "").toUpperCase();
    if (up === "AUTORIZADA") return "status-badge status-autorizada";
    if (up === "RESTRINGIDA") return "status-badge status-restringida";
    return "status-badge status-pendiente";
  }

  function openModal(modalId) {
    const el = document.getElementById(modalId);
    if (el) el.hidden = false;
  }

  function closeModal(modalId) {
    const el = document.getElementById(modalId);
    if (el) el.hidden = true;
  }

  function closeAllModals() {
    qsa(".modal-backdrop").forEach((m) => {
      m.hidden = true;
    });
  }

  function setAgentOrderContext(orderCode) {
    state.agentOrderContext = orderCode || null;
    const bar = qs("#agent-order-context");
    const label = qs("#agent-order-context-label");
    if (!bar || !label) return;
    if (state.agentOrderContext) {
      label.textContent = `Orden vinculada: ${state.agentOrderContext}`;
      bar.hidden = false;
    } else {
      bar.hidden = true;
    }
  }

  function appendAgentMessage(roleLabel, text, variant, citations) {
    const log = qs("#agent-messages");
    if (!log) return;
    const article = document.createElement("article");
    article.className = `agent-msg agent-msg-${variant}`;
    let badgesHtml = "";
    if (Array.isArray(citations) && citations.length > 0) {
      badgesHtml = `<div class="agent-citations">${citations
        .map((c) => `<span class="citation-pill">${escapeHtml(c)}</span>`)
        .join("")}</div>`;
    }
    article.innerHTML = `<span class="agent-msg-role">${escapeHtml(
      roleLabel
    )}</span><p>${escapeHtml(text)}</p>${badgesHtml}`;
    log.appendChild(article);
    log.scrollTop = log.scrollHeight;
  }

  async function submitClinicalAgentPrompt(promptText) {
    const trimmed = String(promptText || "").trim();
    if (!trimmed) return;

    const btn = qs("#btn-submit-agent");
    appendAgentMessage("Medico Auditor", trimmed, "user", []);
    if (btn) btn.disabled = true;

    try {
      const resp = await fetch("/api/agent/assist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: trimmed,
          order_code: state.agentOrderContext,
        }),
      });
      const data = await resp.json();
      if (resp.status === 403 || data.verdict === "BLOCKED") {
        const reason =
          data.reason || "Solicitud bloqueada por politica de seguridad clinica.";
        const filterTag = data.filter_match ? [data.filter_match] : [];
        appendAgentMessage("Control de Seguridad IA", reason, "blocked", filterTag);
      } else if (resp.ok) {
        appendAgentMessage(
          "Asistente Clinico IA",
          data.answer || "Sin respuesta disponible.",
          "assistant",
          data.citations || []
        );
      } else {
        appendAgentMessage(
          "Asistente Clinico IA",
          data.detail || "Error temporal al procesar la consulta clinica.",
          "blocked",
          []
        );
      }
    } catch (_err) {
      appendAgentMessage(
        "Asistente Clinico IA",
        "No fue posible conectar con el servicio de auditoria clinica.",
        "blocked",
        []
      );
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  function populateOrderDefaults() {
    const form = qs("#form-create-order");
    if (!form || !state.defaults) return;
    Object.entries(state.defaults).forEach(([key, val]) => {
      const field = form.elements.namedItem(key);
      if (field) field.value = val;
    });
  }

  function renderOrdersTable(items) {
    const tbody = qs("#orders-tbody");
    if (!tbody) return;
    if (!items || items.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="8">No se encontraron autorizaciones para el filtro seleccionado.</td></tr>';
      return;
    }

    tbody.innerHTML = items
      .map(
        (item) => `
        <tr>
          <td>
            <span class="code-mono">${escapeHtml(item.order_code)}</span>
            <span class="sub-cell">${escapeHtml(item.folio_number || "")}</span>
          </td>
          <td>
            <strong>${escapeHtml(item.patient_alias)}</strong>
            <span class="sub-cell">${escapeHtml(item.document_masked)} · ${escapeHtml(item.eps_name || "")}</span>
          </td>
          <td><span class="cups-pill">${escapeHtml(item.cups_code || "")}</span></td>
          <td>
            <span>${escapeHtml(item.procedure_name)}</span>
            <span class="sub-cell">${escapeHtml(item.cie10_code || "")}</span>
          </td>
          <td>${escapeHtml(item.specialty)}</td>
          <td>${escapeHtml(item.center_city)}</td>
          <td><span class="${statusBadgeClass(item.status)}">${escapeHtml(item.status)}</span></td>
          <td class="col-right">
            <button type="button" class="btn btn-subtle" data-view-order="${escapeHtml(item.order_code)}">
              Orden PDF
            </button>
          </td>
        </tr>`
      )
      .join("");
  }

  async function loadOrderDefaults() {
    const resp = await fetch("/api/orders/defaults", { cache: "no-store" });
    if (!resp.ok) return;
    state.defaults = await resp.json();
    populateOrderDefaults();
  }

  async function loadOrders() {
    const url =
      state.statusFilter && state.statusFilter !== "ALL"
        ? `/api/orders?status=${encodeURIComponent(state.statusFilter)}`
        : "/api/orders";
    const resp = await fetch(url, { cache: "no-store" });
    if (!resp.ok) return;
    const data = await resp.json();
    renderOrdersTable(data.items || []);
    if (data.kpis) {
      const k = data.kpis;
      const elActive = qs("#kpi-active");
      const elAuth = qs("#kpi-authorized");
      const elPend = qs("#kpi-pending");
      const elCenters = qs("#kpi-centers");
      if (elActive) elActive.textContent = String(k.active_orders ?? "0");
      if (elAuth) elAuth.textContent = String(k.authorized_count ?? k.authorized_today ?? "0");
      if (elPend) elPend.textContent = String(k.pending_count ?? k.pending_signature ?? "0");
      if (elCenters) elCenters.textContent = String(k.regional_centers ?? "4 sedes");
    }
  }

  async function runSearch(queryText) {
    if (!queryText.trim()) {
      await loadOrders();
      return;
    }
    const resp = await fetch(`/api/orders/search?q=${encodeURIComponent(queryText)}`, {
      cache: "no-store",
    });
    if (!resp.ok) return;
    const data = await resp.json();
    renderOrdersTable(data.items || []);
  }

  async function openOrderDetailModal(orderCode) {
    if (!orderCode) return;
    const resp = await fetch(`/api/orders/${encodeURIComponent(orderCode)}`, {
      cache: "no-store",
    });
    if (!resp.ok) return;
    const data = await resp.json();
    const item = data.item;
    if (!item) return;

    state.selectedOrderCode = item.order_code;

    const pdfUrl =
      data.support_pdf_url || `/api/orders/${encodeURIComponent(item.order_code)}/support.pdf`;
    const titleEl = qs("#title-order-detail");
    const gridEl = qs("#detail-meta-grid");
    const folioEl = qs("#detail-folio-label");
    const linkEl = qs("#link-download-pdf");
    const frameEl = qs("#iframe-pdf-preview");

    if (titleEl) titleEl.textContent = `Autorizacion ${item.order_code}`;
    if (gridEl) {
      gridEl.innerHTML = `
        <div class="meta-tile"><span>Afiliado / Documento</span><strong>${escapeHtml(item.patient_alias)} (${escapeHtml(item.document_masked)})</strong></div>
        <div class="meta-tile"><span>CUPS / Especialidad</span><strong>${escapeHtml(item.cups_code || "-")} · ${escapeHtml(item.specialty)}</strong></div>
        <div class="meta-tile"><span>EAPB / Sede</span><strong>${escapeHtml(item.eps_name || "EPS")} · ${escapeHtml(item.center_city)}</strong></div>
        <div class="meta-tile meta-summary"><span>Diagnostico CIE-10 y Pertinencia</span><strong>${escapeHtml(item.cie10_code || "-")} — ${escapeHtml(item.clinical_summary)}</strong></div>
      `;
    }
    if (folioEl) {
      folioEl.textContent = `Folio electronico ${item.folio_number || item.order_code} · ${item.attending_physician || ""}`;
    }
    if (linkEl) linkEl.href = pdfUrl;
    if (frameEl) frameEl.src = pdfUrl;
    openModal("modal-order-detail");
  }

  function bindEvents() {
    qs("#btn-open-new-order")?.addEventListener("click", () => {
      populateOrderDefaults();
      openModal("modal-new-order");
    });

    qs("#btn-open-clinical-agent")?.addEventListener("click", () => {
      setAgentOrderContext(null);
      openModal("modal-clinical-agent");
      qs("#input-agent-prompt")?.focus();
    });

    qs("#btn-ask-agent-from-order")?.addEventListener("click", () => {
      const targetOrder = state.selectedOrderCode;
      closeModal("modal-order-detail");
      setAgentOrderContext(targetOrder);
      openModal("modal-clinical-agent");
      const input = qs("#input-agent-prompt");
      if (input && targetOrder) {
        input.value = `Validar pertinencia clinica CUPS / CIE-10 y preparacion de la orden ${targetOrder}`;
        input.focus();
      }
    });

    qs("#btn-clear-agent-order")?.addEventListener("click", () => {
      setAgentOrderContext(null);
    });

    qs("#form-clinical-agent")?.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const input = qs("#input-agent-prompt");
      if (!input) return;
      const promptVal = input.value;
      input.value = "";
      await submitClinicalAgentPrompt(promptVal);
    });

    qsa("[data-close-modal]").forEach((btn) => {
      btn.addEventListener("click", () => closeModal(btn.dataset.closeModal));
    });

    qsa(".modal-backdrop").forEach((backdrop) => {
      backdrop.addEventListener("click", (ev) => {
        if (ev.target === backdrop) backdrop.hidden = true;
      });
    });

    document.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape") closeAllModals();
    });

    qsa("[data-status-filter]").forEach((pill) => {
      pill.addEventListener("click", async () => {
        qsa("[data-status-filter]").forEach((p) => p.classList.remove("active"));
        pill.classList.add("active");
        state.statusFilter = pill.dataset.statusFilter;
        await loadOrders();
      });
    });

    qs("#form-search")?.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      await runSearch(qs("#input-search").value);
    });

    qs("#orders-tbody")?.addEventListener("click", (ev) => {
      const btn = ev.target.closest("[data-view-order]");
      if (btn) openOrderDetailModal(btn.dataset.viewOrder);
    });

    qs("#form-create-order")?.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const fd = new FormData(ev.target);
      const body = Object.fromEntries(fd.entries());
      const resp = await fetch("/api/orders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (resp.ok) {
        closeModal("modal-new-order");
        populateOrderDefaults();
        await loadOrders();
      }
    });

    const params = new URLSearchParams(window.location.search);
    if (params.get("openModal") === "new-order") {
      openModal("modal-new-order");
    } else if (params.get("openModal") === "clinical-agent") {
      openModal("modal-clinical-agent");
    } else if (params.get("openOrder")) {
      openOrderDetailModal(params.get("openOrder"));
    }
  }

  document.addEventListener("DOMContentLoaded", async () => {
    bindEvents();
    await Promise.all([loadOrderDefaults(), loadOrders()]);
  });
})();
