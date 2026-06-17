import { useEffect, useState, useCallback } from "react";
import api, { errMsg } from "../api/client.js";
import { useToast } from "../components/Toast.jsx";
import MaskedValue from "../components/MaskedValue.jsx";
import DiffViewer from "../components/DiffViewer.jsx";
import Modal from "../components/Modal.jsx";
import Icon from "../components/Icon.jsx";
import { useI18n } from "../i18n.jsx";

const ENVS = ["dev", "staging", "prod", "test"];

export default function EnvFiles() {
  const toast = useToast();
  const { t, lang } = useI18n();
  const [files, setFiles] = useState([]);
  const [selId, setSelId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [snapshots, setSnapshots] = useState([]);
  const [busy, setBusy] = useState(false);

  const [regOpen, setRegOpen] = useState(false);
  const [reg, setReg] = useState({
    name: "",
    file_path: "",
    project_name: "",
    environment: "dev",
  });

  const [entryOpen, setEntryOpen] = useState(false);
  const [entry, setEntry] = useState({ key: "", value: "", comment: "" });

  const [editingEntry, setEditingEntry] = useState(null); // 수정 중인 엔트리
  const [editForm, setEditForm] = useState({ value: "", comment: "" });
  const [editLoading, setEditLoading] = useState(false);

  const [allKeys, setAllKeys] = useState([]); // 연결 모달용 전체 API 키
  const [linkEntryId, setLinkEntryId] = useState(null); // 연결 관리 중인 엔트리 id

  const [diff, setDiff] = useState(null); // {snapshot_id, items}
  const [scanOpen, setScanOpen] = useState(false);
  const [scan, setScan] = useState({ path: "", keys: "" });
  const [scanResult, setScanResult] = useState(null);

  const [entryQuery, setEntryQuery] = useState(""); // 엔트리 검색

  const loadFiles = useCallback(async () => {
    try {
      const { data } = await api.get("/envfiles");
      setFiles(data);
      if (!selId && data.length) setSelId(data[0].id);
    } catch (e) {
      toast.error(errMsg(e));
    }
  }, [toast, selId]);

  const loadDetail = useCallback(
    async (id) => {
      if (!id) return;
      try {
        const [d, s] = await Promise.all([
          api.get(`/envfiles/${id}`),
          api.get(`/envfiles/${id}/snapshots`),
        ]);
        setDetail(d.data);
        setSnapshots(s.data);
      } catch (e) {
        toast.error(errMsg(e));
      }
    },
    [toast]
  );

  const loadKeys = useCallback(async () => {
    try {
      const { data } = await api.get("/keys");
      setAllKeys(data);
    } catch {
      /* 키 없음 무시 */
    }
  }, []);

  useEffect(() => {
    loadFiles();
    loadKeys();
  }, [loadFiles, loadKeys]);
  useEffect(() => {
    loadDetail(selId);
  }, [selId, loadDetail]);

  const registerFile = async () => {
    try {
      const { data } = await api.post("/envfiles", reg);
      toast.success(t("env.registered"));
      setRegOpen(false);
      setReg({ name: "", file_path: "", project_name: "", environment: "dev" });
      await loadFiles();
      setSelId(data.id);
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const unregister = async () => {
    if (!window.confirm(t("env.unregisterConfirm"))) return;
    try {
      await api.delete(`/envfiles/${selId}`);
      toast.success(t("env.unregistered"));
      setSelId(null);
      setDetail(null);
      loadFiles();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const sync = async (dir) => {
    setBusy(true);
    try {
      const { data } = await api.post(`/envfiles/${selId}/sync/${dir}`);
      toast.success(data.message);
      loadDetail(selId);
      loadFiles();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };

  const snapshot = async () => {
    try {
      await api.post(`/envfiles/${selId}/snapshot`);
      toast.success(t("env.snapshotSaved"));
      loadDetail(selId);
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const addEntry = async () => {
    try {
      await api.post(`/envfiles/${selId}/entries`, entry);
      toast.success(t("env.entryAdded"));
      setEntryOpen(false);
      setEntry({ key: "", value: "", comment: "" });
      loadDetail(selId);
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const delEntry = async (eid, key) => {
    if (!window.confirm(t("env.entryDeleteConfirm", { key }))) return;
    try {
      await api.delete(`/envfiles/${selId}/entries/${eid}`);
      toast.success(t("env.entryDeleted"));
      loadDetail(selId);
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const openEditEntry = async (e) => {
    setEditingEntry(e);
    setEditForm({ value: "", comment: e.comment || "" });
    setEditLoading(true);
    try {
      // 현재 값은 암호화 저장이라 별도 복호화 요청으로 채운다
      const { data } = await api.get(
        `/envfiles/${selId}/entries/${e.id}/value`
      );
      setEditForm({ value: data.value, comment: e.comment || "" });
    } catch (err) {
      toast.error(errMsg(err, t("env.valueLoadFail")));
    } finally {
      setEditLoading(false);
    }
  };

  const saveEditEntry = async () => {
    try {
      await api.put(`/envfiles/${selId}/entries/${editingEntry.id}`, {
        value: editForm.value,
        comment: editForm.comment,
      });
      toast.success(t("env.entryUpdated"));
      setEditingEntry(null);
      loadDetail(selId);
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const toggleLink = async (entryId, keyId, linked) => {
    try {
      const url = `/envfiles/${selId}/entries/${entryId}/links/${keyId}`;
      if (linked) await api.delete(url);
      else await api.post(url);
      await loadDetail(selId); // linked_key_ids 갱신
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const showDiff = async (snapId) => {
    try {
      const { data } = await api.get(`/envfiles/${selId}/diff/${snapId}`);
      setDiff(data);
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const restore = async (snapId) => {
    if (!window.confirm(t("env.restoreConfirm"))) return;
    try {
      await api.post(`/envfiles/${selId}/snapshots/${snapId}/restore`);
      toast.success(t("env.restored"));
      loadDetail(selId);
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const runScan = async () => {
    try {
      const body = { path: scan.path };
      if (scan.keys.trim())
        body.keys = scan.keys
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);
      const { data } = await api.post("/envfiles/scan", body);
      setScanResult(data);
    } catch (e) {
      toast.error(errMsg(e));
    }
  };

  const linkEntry = detail?.entries.find((e) => e.id === linkEntryId) || null;

  // 환경별 파일 그룹 (dev → staging → prod → test → 기타 순)
  const ENV_ORDER = ["dev", "staging", "prod", "test"];
  const groupedFiles = [...files].sort(
    (a, b) =>
      (ENV_ORDER.indexOf(a.environment) + 1 || 99) -
      (ENV_ORDER.indexOf(b.environment) + 1 || 99)
  );
  const fileGroups = groupedFiles.reduce((acc, f) => {
    (acc[f.environment] ||= []).push(f);
    return acc;
  }, {});
  const groupOrder = Object.keys(fileGroups).sort(
    (a, b) =>
      (ENV_ORDER.indexOf(a) + 1 || 99) - (ENV_ORDER.indexOf(b) + 1 || 99)
  );

  // 선택된 파일의 엔트리 검색 필터
  const eq = entryQuery.trim().toLowerCase();
  const visibleEntries = detail
    ? eq
      ? detail.entries.filter((e) => e.key.toLowerCase().includes(eq))
      : detail.entries
    : [];

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t("env.title")}</h1>
        <div className="flex gap-2">
          <button className="btn-outline gap-1.5" onClick={() => setScanOpen(true)}>
            <Icon name="search" size={16} /> {t("env.scan")}
          </button>
          <button className="btn-primary gap-1.5" onClick={() => setRegOpen(true)}>
            <Icon name="plus" size={16} /> {t("env.registerFile")}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[260px_1fr]">
        {/* 파일 목록 (환경별 그룹) */}
        <div className="card h-fit p-2">
          {files.length === 0 ? (
            <p className="p-4 text-center text-sm text-slate-500">
              {t("env.noFiles")}
            </p>
          ) : (
            groupOrder.map((env) => (
              <div key={env} className="mb-2">
                <div className="px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                  {env} ({fileGroups[env].length})
                </div>
                {fileGroups[env].map((f) => (
                  <button
                    key={f.id}
                    onClick={() => setSelId(f.id)}
                    className={`mb-1 block w-full rounded-lg px-3 py-2 text-left text-sm ${
                      f.id === selId
                        ? "bg-brand-50 text-brand-700 dark:bg-brand-600/15 dark:text-brand-400"
                        : "hover:bg-slate-100 dark:hover:bg-slate-800"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="truncate font-medium">{f.name}</span>
                      <span
                        className={`ml-2 rounded px-1.5 py-0.5 text-[10px] ${
                          f.file_exists
                            ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300"
                            : "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300"
                        }`}
                      >
                        {f.file_exists ? t("env.exists") : t("env.missing")}
                      </span>
                    </div>
                    <div className="truncate text-xs text-slate-400">
                      {f.project_name || f.environment} ·{" "}
                      {t("env.count", { n: f.entry_count })}
                    </div>
                  </button>
                ))}
              </div>
            ))
          )}
        </div>

        {/* 상세 */}
        <div className="space-y-4">
          {!detail ? (
            <div className="card p-10 text-center text-slate-500">
              {t("env.selectFile")}
            </div>
          ) : (
            <>
              <div className="card p-4">
                <div className="flex items-start justify-between">
                  <div className="min-w-0">
                    <h2 className="text-lg font-semibold">{detail.name}</h2>
                    <p className="truncate font-mono text-xs text-slate-400">
                      {detail.file_path}
                    </p>
                    {detail.last_synced_at && (
                      <p className="text-xs text-slate-400">
                        {t("env.lastSynced", {
                          time: new Date(detail.last_synced_at).toLocaleString(lang),
                        })}
                      </p>
                    )}
                  </div>
                  <button
                    className="btn-ghost px-2 py-1 text-xs text-red-600"
                    onClick={unregister}
                  >
                    {t("env.unregister")}
                  </button>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    className="btn-outline gap-1.5 text-xs"
                    onClick={() => sync("pull")}
                    disabled={busy}
                  >
                    <Icon name="download" size={14} /> {t("env.pull")}
                  </button>
                  <button
                    className="btn-outline gap-1.5 text-xs"
                    onClick={() => sync("push")}
                    disabled={busy}
                  >
                    <Icon name="upload" size={14} /> {t("env.push")}
                  </button>
                  <button className="btn-outline gap-1.5 text-xs" onClick={snapshot}>
                    <Icon name="camera" size={14} /> {t("env.snapshot")}
                  </button>
                  <button
                    className="btn-primary gap-1.5 text-xs"
                    onClick={() => {
                      setEntry({ key: "", value: "", comment: "" });
                      setEntryOpen(true);
                    }}
                  >
                    <Icon name="plus" size={14} /> {t("env.entry")}
                  </button>
                </div>
              </div>

              {/* 엔트리 */}
              <div className="card p-4">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <h3 className="font-semibold">
                    {t("env.entriesTitle", { n: detail.entries.length })}
                  </h3>
                  {detail.entries.length > 0 && (
                    <div className="relative max-w-[200px] flex-1">
                      <Icon
                        name="search"
                        size={14}
                        className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400"
                      />
                      <input
                        className="input py-1 pl-8 text-xs"
                        placeholder={t("env.entrySearchPlaceholder")}
                        value={entryQuery}
                        onChange={(e) => setEntryQuery(e.target.value)}
                      />
                    </div>
                  )}
                </div>
                {detail.entries.length === 0 ? (
                  <p className="py-4 text-center text-sm text-slate-500">
                    {t("env.noEntries")}
                  </p>
                ) : visibleEntries.length === 0 ? (
                  <p className="py-4 text-center text-sm text-slate-500">
                    {t("env.noEntryResults", { q: entryQuery })}
                  </p>
                ) : (
                  <div className="space-y-2">
                    {visibleEntries.map((e) => (
                      <div
                        key={e.id}
                        className="rounded-lg border border-slate-100 p-3 dark:border-slate-800"
                      >
                        <div className="flex items-center justify-between">
                          <code className="font-mono text-sm font-semibold">
                            {e.key}
                          </code>
                          <div className="flex gap-1">
                            <button
                              className="btn-ghost gap-1 px-2 py-0.5 text-xs"
                              onClick={() => setLinkEntryId(e.id)}
                            >
                              <Icon name="link" size={13} /> {t("env.link")}
                              {e.linked_key_ids?.length
                                ? ` (${e.linked_key_ids.length})`
                                : ""}
                            </button>
                            <button
                              className="btn-ghost gap-1 px-2 py-0.5 text-xs"
                              onClick={() => openEditEntry(e)}
                            >
                              <Icon name="pencil" size={13} /> {t("common.edit")}
                            </button>
                            <button
                              className="btn-ghost px-2 py-0.5 text-xs text-red-600"
                              onClick={() => delEntry(e.id, e.key)}
                              title={t("common.delete")}
                            >
                              <Icon name="trash" size={13} />
                            </button>
                          </div>
                        </div>
                        {e.comment && (
                          <p className="mt-1 text-xs text-slate-400">
                            # {e.comment}
                          </p>
                        )}
                        <div className="mt-2">
                          <MaskedValue
                            getValue={() =>
                              api
                                .get(
                                  `/envfiles/${selId}/entries/${e.id}/value`
                                )
                                .then((r) => r.data.value)
                            }
                          />
                        </div>
                        {e.linked_key_ids?.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-1">
                            {e.linked_key_ids.map((kid) => {
                              const k = allKeys.find((x) => x.id === kid);
                              return (
                                <span
                                  key={kid}
                                  className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-2 py-0.5 text-xs text-brand-700 dark:bg-brand-600/15 dark:text-brand-400"
                                >
                                  <Icon name="key" size={12} />{" "}
                                  {k ? k.name : `#${kid}`}
                                </span>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* 스냅샷 */}
              <div className="card p-4">
                <h3 className="mb-3 font-semibold">
                  {t("env.snapshotsTitle", { n: snapshots.length })}
                </h3>
                {snapshots.length === 0 ? (
                  <p className="py-4 text-center text-sm text-slate-500">
                    {t("env.noSnapshots")}
                  </p>
                ) : (
                  <ul className="divide-y divide-slate-100 dark:divide-slate-800">
                    {snapshots.map((s) => (
                      <li
                        key={s.id}
                        className="flex items-center justify-between py-2 text-sm"
                      >
                        <div>
                          <div className="font-medium">
                            {s.label || t("env.snapshotDefault")}
                          </div>
                          <div className="text-xs text-slate-400">
                            {new Date(s.created_at).toLocaleString(lang)} ·{" "}
                            {t("env.count", { n: s.entry_count })}
                          </div>
                        </div>
                        <div className="flex gap-1">
                          <button
                            className="btn-ghost px-2 py-1 text-xs"
                            onClick={() => showDiff(s.id)}
                          >
                            {t("env.diff")}
                          </button>
                          <button
                            className="btn-outline px-2 py-1 text-xs"
                            onClick={() => restore(s.id)}
                          >
                            {t("env.restore")}
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* 파일 등록 */}
      <Modal
        open={regOpen}
        onClose={() => setRegOpen(false)}
        title={t("env.registerTitle")}
        footer={
          <>
            <button className="btn-ghost" onClick={() => setRegOpen(false)}>
              {t("common.cancel")}
            </button>
            <button className="btn-primary" onClick={registerFile}>
              {t("common.add")}
            </button>
          </>
        }
      >
        <div className="space-y-3">
          <div>
            <label className="label">{t("env.regName")}</label>
            <input
              className="input"
              value={reg.name}
              onChange={(e) => setReg({ ...reg, name: e.target.value })}
            />
          </div>
          <div>
            <label className="label">{t("env.regPath")}</label>
            <input
              className="input font-mono"
              value={reg.file_path}
              onChange={(e) => setReg({ ...reg, file_path: e.target.value })}
              placeholder={t("env.regPathPlaceholder")}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">{t("env.regProject")}</label>
              <input
                className="input"
                value={reg.project_name}
                onChange={(e) =>
                  setReg({ ...reg, project_name: e.target.value })
                }
              />
            </div>
            <div>
              <label className="label">{t("env.regEnv")}</label>
              <select
                className="input"
                value={reg.environment}
                onChange={(e) =>
                  setReg({ ...reg, environment: e.target.value })
                }
              >
                {ENVS.map((x) => (
                  <option key={x}>{x}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </Modal>

      {/* 엔트리 추가 */}
      <Modal
        open={entryOpen}
        onClose={() => setEntryOpen(false)}
        title={t("env.entryAddTitle")}
        footer={
          <>
            <button className="btn-ghost" onClick={() => setEntryOpen(false)}>
              {t("common.cancel")}
            </button>
            <button className="btn-primary" onClick={addEntry}>
              {t("common.add")}
            </button>
          </>
        }
      >
        <div className="space-y-3">
          <div>
            <label className="label">{t("env.entryKey")}</label>
            <input
              className="input font-mono"
              value={entry.key}
              onChange={(e) =>
                setEntry({ ...entry, key: e.target.value.toUpperCase() })
              }
              placeholder={t("env.entryKeyPlaceholder")}
            />
          </div>
          <div>
            <label className="label">{t("env.entryValue")}</label>
            <input
              className="input font-mono"
              value={entry.value}
              onChange={(e) => setEntry({ ...entry, value: e.target.value })}
            />
          </div>
          <div>
            <label className="label">{t("env.entryComment")}</label>
            <input
              className="input"
              value={entry.comment}
              onChange={(e) => setEntry({ ...entry, comment: e.target.value })}
            />
          </div>
        </div>
      </Modal>

      {/* 엔트리 수정 */}
      <Modal
        open={!!editingEntry}
        onClose={() => setEditingEntry(null)}
        title={t("env.entryEditTitle", { key: editingEntry?.key || "" })}
        footer={
          <>
            <button className="btn-ghost" onClick={() => setEditingEntry(null)}>
              {t("common.cancel")}
            </button>
            <button
              className="btn-primary"
              onClick={saveEditEntry}
              disabled={editLoading}
            >
              {t("common.save")}
            </button>
          </>
        }
      >
        <div className="space-y-3">
          <div>
            <label className="label">{t("env.entryValue")}</label>
            <input
              className="input font-mono"
              value={editForm.value}
              onChange={(e) =>
                setEditForm({ ...editForm, value: e.target.value })
              }
              placeholder={editLoading ? t("env.valueLoading") : ""}
              disabled={editLoading}
            />
          </div>
          <div>
            <label className="label">{t("env.entryComment")}</label>
            <input
              className="input"
              value={editForm.comment}
              onChange={(e) =>
                setEditForm({ ...editForm, comment: e.target.value })
              }
            />
          </div>
        </div>
      </Modal>

      {/* 키 연결 관리 */}
      <Modal
        open={!!linkEntry}
        onClose={() => setLinkEntryId(null)}
        title={t("env.linkTitle", { key: linkEntry?.key || "" })}
      >
        {allKeys.length === 0 ? (
          <p className="py-6 text-center text-sm text-slate-500">
            {t("env.noKeysForLink")}
          </p>
        ) : (
          <ul className="max-h-80 space-y-1 overflow-y-auto">
            {allKeys.map((k) => {
              const linked = linkEntry?.linked_key_ids?.includes(k.id);
              return (
                <li
                  key={k.id}
                  className="flex items-center justify-between rounded-lg px-2 py-1.5 hover:bg-slate-50 dark:hover:bg-slate-800"
                >
                  <span className="flex items-center gap-2 text-sm">
                    <span className="font-medium">{k.name}</span>
                    <span className="text-xs text-slate-400">{k.service}</span>
                  </span>
                  <button
                    className={linked ? "btn-outline px-2 py-1 text-xs" : "btn-primary px-2 py-1 text-xs"}
                    onClick={() => toggleLink(linkEntry.id, k.id, linked)}
                  >
                    {linked ? t("env.unlinkBtn") : t("env.linkBtn")}
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </Modal>

      {/* diff */}
      <Modal
        open={!!diff}
        onClose={() => setDiff(null)}
        title={t("env.diffTitle", { id: diff?.snapshot_id })}
        wide
      >
        <DiffViewer items={diff?.items} />
      </Modal>

      {/* 스캔 */}
      <Modal
        open={scanOpen}
        onClose={() => {
          setScanOpen(false);
          setScanResult(null);
        }}
        title={t("env.scanTitle")}
        wide
        footer={
          <>
            <button
              className="btn-ghost"
              onClick={() => {
                setScanOpen(false);
                setScanResult(null);
              }}
            >
              {t("common.close")}
            </button>
            <button className="btn-primary" onClick={runScan}>
              {t("env.scanBtn")}
            </button>
          </>
        }
      >
        <div className="space-y-3">
          <div>
            <label className="label">{t("env.scanDir")}</label>
            <input
              className="input font-mono"
              value={scan.path}
              onChange={(e) => setScan({ ...scan, path: e.target.value })}
              placeholder={t("env.scanDirPlaceholder")}
            />
          </div>
          <div>
            <label className="label">{t("env.scanKeys")}</label>
            <input
              className="input font-mono"
              value={scan.keys}
              onChange={(e) => setScan({ ...scan, keys: e.target.value })}
              placeholder={t("env.scanKeysPlaceholder")}
            />
          </div>
          {scanResult && (
            <div className="mt-2">
              <p className="mb-2 text-sm text-slate-500">
                {t("env.scanSummary", {
                  files: scanResult.scanned_files,
                  matches: scanResult.matches.length,
                })}
                {scanResult.truncated && t("env.scanTruncated")}
              </p>
              <div className="max-h-72 overflow-y-auto rounded-lg border border-slate-100 dark:border-slate-800">
                {scanResult.matches.length === 0 ? (
                  <p className="p-4 text-center text-sm text-slate-500">
                    {t("env.noMatch")}
                  </p>
                ) : (
                  scanResult.matches.map((m, i) => (
                    <div
                      key={i}
                      className="border-b border-slate-100 px-3 py-2 text-xs dark:border-slate-800"
                    >
                      <div className="flex justify-between">
                        <code className="font-semibold text-brand-600">
                          {m.key}
                        </code>
                        <span className="text-slate-400">
                          {m.file}:{m.line_no}
                        </span>
                      </div>
                      <code className="mt-1 block truncate font-mono text-slate-500">
                        {m.line}
                      </code>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </Modal>
    </div>
  );
}
