import { useEffect, useState, useCallback } from "react";
import api, { errMsg } from "../api/client.js";
import { useToast } from "../components/Toast.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import ServiceIcon from "../components/ServiceIcon.jsx";
import MaskedValue from "../components/MaskedValue.jsx";
import Modal from "../components/Modal.jsx";
import Icon from "../components/Icon.jsx";
import { SERVICE_LIST, detectService } from "../services.js";
import { useI18n } from "../i18n.jsx";

const EMPTY = {
  name: "",
  service: "openai",
  value: "",
  description: "",
  tags: "",
  expires_at: "",
};

function KeyForm({ form, setForm, withValue }) {
  const { t } = useI18n();
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  // 키 값 입력 시 서비스 자동 감지
  const onValueChange = (e) => {
    const value = e.target.value;
    const detected = detectService(value);
    setForm((f) => ({
      ...f,
      value,
      ...(detected ? { service: detected, _autoDetected: true } : {}),
    }));
  };

  return (
    <div className="space-y-3">
      <div>
        <label className="label">{t("keys.fName")}</label>
        <input className="input" value={form.name} onChange={set("name")} />
      </div>
      <div>
        <label className="label">{t("keys.fService")}</label>
        <div className="flex items-center gap-2">
          <ServiceIcon service={form.service} size={36} />
          <select
            className="input"
            value={form.service}
            onChange={(e) =>
              setForm((f) => ({
                ...f,
                service: e.target.value,
                _autoDetected: false,
              }))
            }
          >
            {SERVICE_LIST.map((s) => (
              <option key={s.service} value={s.service}>
                {s.label}
              </option>
            ))}
            <option value="other">{t("service.other")}</option>
          </select>
        </div>
        {form._autoDetected && (
          <p className="mt-1 flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400">
            <Icon name="check" size={13} /> {t("keys.autoDetected")}
          </p>
        )}
      </div>
      <div>
        <label className="label">
          {withValue ? t("keys.fValue") : t("keys.fValueKeep")}
        </label>
        <input
          className="input font-mono"
          value={form.value}
          onChange={onValueChange}
          placeholder={
            withValue ? t("keys.fValuePlaceholder") : t("keys.fValueEditPlaceholder")
          }
        />
      </div>
      <div>
        <label className="label">{t("keys.fDescription")}</label>
        <input
          className="input"
          value={form.description || ""}
          onChange={set("description")}
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label">{t("keys.fTags")}</label>
          <input
            className="input"
            value={form.tags || ""}
            onChange={set("tags")}
            placeholder={t("keys.fTagsPlaceholder")}
          />
        </div>
        <div>
          <label className="label">{t("keys.fExpiresAt")}</label>
          <input
            type="date"
            className="input"
            value={form.expires_at ? form.expires_at.slice(0, 10) : ""}
            onChange={set("expires_at")}
          />
        </div>
      </div>
    </div>
  );
}

export default function ApiKeys() {
  const toast = useToast();
  const { t, lang } = useI18n();
  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState({});
  const [query, setQuery] = useState("");
  const [batchTesting, setBatchTesting] = useState(false);

  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY);

  const [historyKey, setHistoryKey] = useState(null);
  const [history, setHistory] = useState([]);

  const [exportOpen, setExportOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [backupPw, setBackupPw] = useState("");
  const [importContent, setImportContent] = useState("");
  const [importOverwrite, setImportOverwrite] = useState(false);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get("/keys");
      setKeys(data);
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const payload = (f) => {
    const p = { ...f };
    delete p._autoDetected; // UI 전용 플래그 제거
    if (!p.expires_at) p.expires_at = null;
    else p.expires_at = new Date(p.expires_at).toISOString();
    return p;
  };

  const create = async () => {
    try {
      await api.post("/keys", payload(form));
      toast.success(t("keys.created"));
      setCreateOpen(false);
      setForm(EMPTY);
      load();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const save = async () => {
    try {
      const p = payload(form);
      if (!p.value) delete p.value; // 비우면 값 유지
      await api.put(`/keys/${editing.id}`, p);
      toast.success(t("keys.updated"));
      setEditing(null);
      load();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const remove = async (k) => {
    if (!window.confirm(t("keys.deleteConfirm", { name: k.name }))) return;
    try {
      await api.delete(`/keys/${k.id}`);
      toast.success(t("keys.deleted"));
      load();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const test = async (k) => {
    setTesting((s) => ({ ...s, [k.id]: true }));
    try {
      const { data } = await api.post(`/test/key/${k.id}`);
      toast[data.status === "ok" ? "success" : "error"](data.message);
      load();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setTesting((s) => ({ ...s, [k.id]: false }));
    }
  };

  const testAll = async () => {
    if (!keys.length) return;
    setBatchTesting(true);
    try {
      const { data } = await api.post("/test/batch", {
        key_ids: keys.map((k) => k.id),
      });
      const ok = data.filter((r) => r.status === "ok").length;
      toast.success(t("keys.testAllDone", { ok, total: data.length }));
      load();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBatchTesting(false);
    }
  };

  const openHistory = async (k) => {
    setHistoryKey(k);
    try {
      const { data } = await api.get(`/keys/${k.id}/history`);
      setHistory(data);
    } catch (e) {
      toast.error(errMsg(e));
      setHistory([]);
    }
  };

  const rollback = async (hid) => {
    try {
      await api.post(`/keys/${historyKey.id}/rollback/${hid}`);
      toast.success(t("keys.rollbackDone"));
      setHistoryKey(null);
      load();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const doExport = async () => {
    try {
      const res = await api.post(
        "/keys/export",
        { backup_password: backupPw },
        { responseType: "text" }
      );
      const blob = new Blob([res.data], { type: "application/octet-stream" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "keys.envbackup";
      a.click();
      URL.revokeObjectURL(url);
      toast.success(t("keys.exportDone"));
      setExportOpen(false);
      setBackupPw("");
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const doImport = async () => {
    try {
      const { data } = await api.post("/keys/import", {
        backup_password: backupPw,
        content: importContent,
        overwrite: importOverwrite,
      });
      toast.success(data.message);
      setImportOpen(false);
      setBackupPw("");
      setImportContent("");
      load();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const startEdit = (k) => {
    setEditing(k);
    setForm({
      name: k.name,
      service: k.service,
      value: "",
      description: k.description || "",
      tags: k.tags || "",
      expires_at: k.expires_at || "",
    });
  };

  const q = query.trim().toLowerCase();
  const filtered = q
    ? keys.filter((k) =>
        [k.name, k.service, k.tags, k.description]
          .filter(Boolean)
          .some((s) => s.toLowerCase().includes(q))
      )
    : keys;

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t("keys.title")}</h1>
        <div className="flex gap-2">
          <button
            className="btn-outline gap-1.5"
            onClick={testAll}
            disabled={batchTesting || keys.length === 0}
          >
            <Icon name="beaker" size={16} />
            {batchTesting ? t("keys.testingAll") : t("keys.testAll")}
          </button>
          <button className="btn-outline gap-1.5" onClick={() => setImportOpen(true)}>
            <Icon name="upload" size={16} /> {t("keys.restore")}
          </button>
          <button className="btn-outline gap-1.5" onClick={() => setExportOpen(true)}>
            <Icon name="download" size={16} /> {t("keys.backup")}
          </button>
          <button
            className="btn-primary gap-1.5"
            onClick={() => {
              setForm(EMPTY);
              setCreateOpen(true);
            }}
          >
            <Icon name="plus" size={16} /> {t("keys.addKey")}
          </button>
        </div>
      </div>

      {keys.length > 0 && (
        <div className="relative max-w-sm">
          <Icon
            name="search"
            size={15}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
          />
          <input
            className="input pl-9"
            placeholder={t("keys.searchPlaceholder")}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
      )}

      {loading ? (
        <div className="text-slate-400">{t("common.loading")}</div>
      ) : keys.length === 0 ? (
        <div className="card p-10 text-center text-slate-500">
          {t("keys.empty", { add: t("keys.addKey") })}
        </div>
      ) : filtered.length === 0 ? (
        <div className="card p-10 text-center text-slate-500">
          {t("keys.noResults", { q: query })}
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((k) => (
            <div key={k.id} className="card p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex min-w-0 items-center gap-3">
                  <ServiceIcon service={k.service} />
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">{k.name}</span>
                      <StatusBadge status={k.last_test_status} />
                    </div>
                    <div className="text-xs text-slate-400">
                      {k.service}
                      {k.tags && ` · ${k.tags}`}
                      {k.expires_at &&
                        ` · ${t("keys.expires", { date: k.expires_at.slice(0, 10) })}`}
                    </div>
                  </div>
                </div>
                <div className="flex shrink-0 gap-1">
                  <button
                    className="btn-ghost gap-1 px-2 py-1 text-xs"
                    onClick={() => test(k)}
                    disabled={testing[k.id]}
                  >
                    {testing[k.id] ? (
                      t("keys.testing")
                    ) : (
                      <>
                        <Icon name="beaker" size={14} /> {t("keys.test")}
                      </>
                    )}
                  </button>
                  <button
                    className="btn-ghost gap-1 px-2 py-1 text-xs"
                    onClick={() => openHistory(k)}
                  >
                    <Icon name="history" size={14} /> {t("keys.history")}
                  </button>
                  <button
                    className="btn-ghost gap-1 px-2 py-1 text-xs"
                    onClick={() => startEdit(k)}
                  >
                    <Icon name="pencil" size={14} /> {t("keys.edit")}
                  </button>
                  <button
                    className="btn-ghost px-2 py-1 text-xs text-red-600"
                    onClick={() => remove(k)}
                    title={t("common.delete")}
                  >
                    <Icon name="trash" size={14} />
                  </button>
                </div>
              </div>
              <div className="mt-3">
                <MaskedValue
                  getValue={() =>
                    api.get(`/keys/${k.id}/value`).then((r) => r.data.value)
                  }
                />
              </div>
              {k.last_test_message && (
                <p className="mt-2 text-xs text-slate-400">
                  {k.last_test_message}
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* 생성 */}
      <Modal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title={t("keys.createTitle")}
        footer={
          <>
            <button className="btn-ghost" onClick={() => setCreateOpen(false)}>
              {t("common.cancel")}
            </button>
            <button className="btn-primary" onClick={create}>
              {t("common.add")}
            </button>
          </>
        }
      >
        <KeyForm form={form} setForm={setForm} withValue />
      </Modal>

      {/* 수정 */}
      <Modal
        open={!!editing}
        onClose={() => setEditing(null)}
        title={t("keys.editTitle")}
        footer={
          <>
            <button className="btn-ghost" onClick={() => setEditing(null)}>
              {t("common.cancel")}
            </button>
            <button className="btn-primary" onClick={save}>
              {t("common.save")}
            </button>
          </>
        }
      >
        <KeyForm form={form} setForm={setForm} withValue={false} />
      </Modal>

      {/* 이력 */}
      <Modal
        open={!!historyKey}
        onClose={() => setHistoryKey(null)}
        title={t("keys.historyTitle", { name: historyKey?.name || "" })}
        wide
      >
        {history.length === 0 ? (
          <p className="py-6 text-center text-sm text-slate-500">
            {t("keys.noHistory")}
          </p>
        ) : (
          <ul className="divide-y divide-slate-100 dark:divide-slate-800">
            {history.map((h) => (
              <li
                key={h.id}
                className="flex items-center justify-between py-3 text-sm"
              >
                <div>
                  <div className="font-medium">
                    {new Date(h.changed_at).toLocaleString(lang)}
                  </div>
                  <div className="text-xs text-slate-400">{h.note || "—"}</div>
                </div>
                <button
                  className="btn-outline px-2 py-1 text-xs"
                  onClick={() => rollback(h.id)}
                >
                  {t("keys.rollback")}
                </button>
              </li>
            ))}
          </ul>
        )}
      </Modal>

      {/* 백업 */}
      <Modal
        open={exportOpen}
        onClose={() => setExportOpen(false)}
        title={t("keys.exportTitle")}
        footer={
          <>
            <button className="btn-ghost" onClick={() => setExportOpen(false)}>
              {t("common.cancel")}
            </button>
            <button
              className="btn-primary"
              onClick={doExport}
              disabled={backupPw.length < 8}
            >
              {t("keys.exportBtn")}
            </button>
          </>
        }
      >
        <p className="mb-3 text-sm text-slate-500">{t("keys.exportDesc")}</p>
        <label className="label">{t("keys.backupPw")}</label>
        <input
          type="password"
          className="input"
          value={backupPw}
          onChange={(e) => setBackupPw(e.target.value)}
        />
      </Modal>

      {/* 복원 */}
      <Modal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        title={t("keys.importTitle")}
        wide
        footer={
          <>
            <button className="btn-ghost" onClick={() => setImportOpen(false)}>
              {t("common.cancel")}
            </button>
            <button
              className="btn-primary"
              onClick={doImport}
              disabled={!backupPw || !importContent}
            >
              {t("keys.importBtn")}
            </button>
          </>
        }
      >
        <div className="space-y-3">
          <div>
            <label className="label">{t("keys.importPw")}</label>
            <input
              type="password"
              className="input"
              value={backupPw}
              onChange={(e) => setBackupPw(e.target.value)}
            />
          </div>
          <div>
            <label className="label">{t("keys.importContent")}</label>
            <textarea
              className="input h-32 font-mono text-xs"
              value={importContent}
              onChange={(e) => setImportContent(e.target.value)}
              placeholder={t("keys.importContentPlaceholder")}
            />
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={importOverwrite}
              onChange={(e) => setImportOverwrite(e.target.checked)}
            />
            {t("keys.overwrite")}
          </label>
        </div>
      </Modal>
    </div>
  );
}
