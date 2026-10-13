import { useEffect, useRef, useState } from 'react';

function Modal({ title, onClose, children }) {
  const ref = useRef(null);
  useEffect(() => {
    const dialog = ref.current;
    const previous = document.activeElement;
    dialog.showModal();
    return () => { dialog.close(); previous?.focus(); };
  }, []);
  return <dialog ref={ref} className="modal-dialog" aria-label={title} onCancel={event => { event.preventDefault(); onClose(); }}
    onClick={event => { if (event.target === ref.current) onClose(); }}>
    <div className="modal-container">
      <div className="modal-header"><h3 className="modal-title">{title}</h3>
        <button className="modal-close-btn" onClick={onClose} aria-label="Close dialog">×</button></div>
      {children}
    </div>
  </dialog>;
}

export function ProposalModal({ onClose, lead, onCopyProposal }) {
  const [draft, setDraft] = useState(() => `PARAMANTRA CRM — PROPOSAL DRAFT\nClient: ${lead.name || 'Not recorded'}\nCompany: ${lead.company || 'Not recorded'}\nPrepared by: ${lead.assigned_to || 'Not assigned'}\n\nUser licenses: [Confirm quantity]\nSubscription price and currency: [Confirm approved pricing]\nOnboarding cost: [Confirm]\nScope and delivery timeline: [Confirm]\nCommercial concessions: [Subject to approval]\n\nComplete and verify all terms before sharing with the customer.`);
  return <Modal title="Proposal draft" onClose={onClose}>
    <div className="modal-body"><p className="text-muted">Enter approved commercial terms. Pricing and concessions are not inferred.</p>
      <label className="form-group">Proposal text<textarea rows={16} value={draft} onChange={event => setDraft(event.target.value)} /></label></div>
    <div className="modal-footer"><button className="btn-modal-secondary" onClick={onClose}>Close</button>
      <button className="btn-modal-primary" onClick={async () => { if (await onCopyProposal(draft, 'Proposal draft copied.')) onClose(); }}>Copy draft</button></div>
  </Modal>;
}

export function CompanyProfileModal({ onClose, lead }) {
  return <Modal title={lead.company || 'Account profile'} onClose={onClose}>
    <div className="modal-body"><dl className="company-intel-grid">
      {Object.entries({ Contact: lead.name, Company: lead.company, Stage: lead.stage, Status: lead.status, Owner: lead.assigned_to }).map(([label, value]) =>
        <div className="intel-card" key={label}><dt className="intel-label">{label}</dt><dd className="intel-val">{value || 'Not recorded'}</dd></div>)}
    </dl><p className="text-muted">Company size, revenue, pricing and license scope are not recorded in this profile.</p></div>
    <div className="modal-footer"><button className="btn-modal-primary" onClick={onClose}>Done</button></div>
  </Modal>;
}

export function EditLeadModal({ onClose, lead, onSaveLead }) {
  const [form, setForm] = useState(() => ({ name: lead.name || '', company: lead.company || '', stage: lead.stage || '', status: lead.status || '', assigned_to: lead.assigned_to || '' }));
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const submit = async event => {
    event.preventDefault(); setError(''); setSaving(true);
    const changes = Object.fromEntries(Object.entries(form).filter(([key, value]) => value.trim() !== (lead[key] || '')).map(([key, value]) => [key, value.trim()]));
    if (!Object.keys(changes).length) { setSaving(false); onClose(); return; }
    try { if (await onSaveLead(changes)) onClose(); }
    catch (failure) { setError(failure.message); }
    finally { setSaving(false); }
  };
  return <Modal title={`Edit Lead #${lead.id}`} onClose={() => { if (!saving) onClose(); }}>
    <form onSubmit={submit}><div className="modal-body form-body">
      {Object.entries({ name: 'Contact name', company: 'Company', stage: 'Stage', status: 'Status', assigned_to: 'Assigned rep' }).map(([key, label]) =>
        <label className="form-group" key={key}>{label}<input name={key} value={form[key]} disabled={saving}
          maxLength={key === 'assigned_to' ? 100 : ['stage', 'status'].includes(key) ? 50 : 150}
          onChange={event => setForm(previous => ({ ...previous, [key]: event.target.value }))} /></label>)}
      {error && <p role="alert" className="error-banner">{error}</p>}
    </div><div className="modal-footer"><button type="button" className="btn-modal-secondary" disabled={saving} onClick={onClose}>Cancel</button>
      <button className="btn-modal-primary" disabled={saving} type="submit">{saving ? 'Saving...' : 'Save changes'}</button></div></form>
  </Modal>;
}

export function SpotlightSearchModal({ onClose, leads = [], onSelectLead }) {
  const [query, setQuery] = useState('');
  const filtered = leads.filter(lead => [lead.id, lead.name, lead.company, lead.stage].some(value => String(value ?? '').toLowerCase().includes(query.toLowerCase())));
  return <Modal title="Search CRM leads" onClose={onClose}>
    <div className="modal-body"><label className="form-group">Name, company, stage or ID
      <input value={query} onChange={event => setQuery(event.target.value)} autoFocus /></label>
      <div className="spotlight-results">{filtered.map(lead => <button key={lead.id} className="spotlight-item"
        onClick={() => { onSelectLead(lead.id); onClose(); }}><span>{lead.name || 'Unnamed contact'} · {lead.company || 'No company'}</span><span>#{lead.id}</span></button>)}
        {!filtered.length && <p className="spotlight-empty">No matching leads.</p>}</div>
    </div>
  </Modal>;
}

export function NotificationsPopover({ isOpen, onClose }) {
  if (!isOpen) return null;
  return <div className="notifications-popover"><div className="notif-header"><span>Notifications</span><button onClick={onClose}>Close</button></div>
    <p className="notif-body">Live notification delivery is not connected.</p></div>;
}
