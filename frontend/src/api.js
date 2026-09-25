async function request(path, options = {}) {
  const response = await fetch(path, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail;
    throw new Error(detail || data.message || "Request failed");
  }
  return data;
}

export const api = {
  status: () => request("/api/status"),
  convert: (body) =>
    request("/api/convert", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  missedCharges: (body) =>
    request("/api/missed-charges", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  missedInvoices: (body) =>
    request("/api/missed-invoices", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  batches: (kind) => request(`/api/batches/${kind}`),
  batch: (kind, file) => request(`/api/batches/${kind}/${file}`),
  uploadExcel: async (file) => {
    const form = new FormData();
    form.append("file", file);
    return request("/api/upload-excel", { method: "POST", body: form });
  },
};
