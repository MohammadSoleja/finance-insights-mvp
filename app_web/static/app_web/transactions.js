// Lightweight transactions UI: column resize, modals, AJAX add/bulk edit
(function(){
  'use strict';

  function qs(sel, ctx){ return (ctx||document).querySelector(sel); }
  function qsa(sel, ctx){ return Array.from((ctx||document).querySelectorAll(sel)); }

  function getCookie(name){
    const m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return m ? m.pop() : null;
  }
  const csrftoken = getCookie('csrftoken');

  function showModal(id){ const el = qs('#'+id); if(!el) return; el.style.display='flex'; el.setAttribute('aria-hidden','false'); }
  function hideModal(id){ const el = qs('#'+id); if(!el) return; el.style.display='none'; el.setAttribute('aria-hidden','true'); }

  function initColumnResizer(table){
    if(!table) return;
    const thead = table.tHead || table.querySelector('thead');
    if(!thead) return;
    const ths = Array.from(thead.querySelectorAll('th'));
    ths.forEach((th, idx)=>{
      if(idx === 0) return; // skip select column
      if(!th.querySelector('.col-resizer')){
        const handle = document.createElement('span');
        handle.className = 'col-resizer';
        handle.setAttribute('role','separator');
        handle.setAttribute('aria-orientation','vertical');
        th.appendChild(handle);
      }
    });

    function setColumnWidth(tableEl, index, px){
      const rows = Array.from(tableEl.querySelectorAll('tr'));
      rows.forEach(r=>{ const c = r.children[index]; if(c) c.style.width = px + 'px'; });
    }
    function collectSizes(tableEl){
      const out = {};
      Array.from(tableEl.querySelectorAll('thead th')).forEach(h=>{ if(h.dataset.colIndex) out[h.dataset.colIndex] = Math.round(h.getBoundingClientRect().width); });
      return out;
    }
    function applySizes(tableEl, sizes){
      Array.from(tableEl.querySelectorAll('thead th')).forEach((h,i)=>{
        const key = h.dataset.colIndex;
        if(key && sizes[key]){ const px = parseInt(sizes[key],10); h.style.width = px + 'px'; setColumnWidth(tableEl, i, px); }
      });
    }

    ths.forEach((th, i)=> th.dataset.colIndex = i);

    const saved = (function(){ try{ const s = localStorage.getItem('transactions_col_widths'); return s? JSON.parse(s): null }catch(e){return null;} })();
    if(saved) applySizes(table, saved);

    let dragging = null, startX = 0, startW = 0, origTh = null;
    function onDown(e){ const t = e.target; if(!t.classList.contains('col-resizer')) return; e.preventDefault(); dragging = t; origTh = t.parentElement; startX = (e.touches? e.touches[0].clientX : e.clientX); startW = origTh.getBoundingClientRect().width; document.documentElement.classList.add('resizing'); window.addEventListener('mousemove', onMove); window.addEventListener('touchmove', onMove, {passive:false}); window.addEventListener('mouseup', onUp); window.addEventListener('touchend', onUp); }
    function onMove(e){ if(!dragging) return; e.preventDefault(); const clientX = (e.touches? e.touches[0].clientX : e.clientX); const dx = clientX - startX; const newW = Math.max(60, Math.round(startW + dx)); origTh.style.width = newW + 'px'; const idx = Array.prototype.indexOf.call(origTh.parentElement.children, origTh); setColumnWidth(table, idx, newW); }
    function onUp(){ if(!dragging) return; try{ const sizes = collectSizes(table); localStorage.setItem('transactions_col_widths', JSON.stringify(sizes)); }catch(e){} dragging = null; origTh = null; document.documentElement.classList.remove('resizing'); window.removeEventListener('mousemove', onMove); window.removeEventListener('touchmove', onMove); window.removeEventListener('mouseup', onUp); window.removeEventListener('touchend', onUp); }

    document.addEventListener('mousedown', onDown);
    document.addEventListener('touchstart', onDown, {passive:false});
    table.style.tableLayout = 'fixed';
  }

  function init(){
    try{
      console.debug('[transactions] init');

      // basic selectors
      const table = qs('.preview-table');
      initColumnResizer(table);

      const selectAll = qs('#select-all');
      const rowCheckboxes = ()=> Array.from(document.querySelectorAll('.row-select'));

      function updateActionButtons(){
        const selected = rowCheckboxes().filter(cb=>cb.checked).map(cb=>cb.dataset.id);
        const editBtn = qs('#edit-selected'); const delBtn = qs('#delete-selected');
        if(editBtn) editBtn.disabled = selected.length === 0;
        if(delBtn) delBtn.disabled = selected.length === 0;
      }

      // set initial state of action buttons
      updateActionButtons();

      if(selectAll) selectAll.addEventListener('change', ()=>{ rowCheckboxes().forEach(cb=>cb.checked = selectAll.checked); updateActionButtons(); });
      document.addEventListener('change', function(e){ if(e.target && e.target.classList && e.target.classList.contains('row-select')) updateActionButtons(); });

      // Reset filters
      const resetBtn = qs('#reset-filters');
      if(resetBtn) resetBtn.addEventListener('click', function(){ const f = qs('#filters-form'); if(!f) return; Array.from(f.querySelectorAll('input[name], select[name]')).forEach(el=>{ if(el.name && el.type !== 'submit' && el.type !== 'button') el.value = ''; }); f.submit(); });

      // Add transaction modal
      const addBtn = qs('#add-tx-btn'); if(addBtn) addBtn.addEventListener('click', ()=> showModal('add-tx-modal'));
      const addCancel = qs('#add-tx-cancel'); if(addCancel) addCancel.addEventListener('click', ()=> hideModal('add-tx-modal'));
      const addForm = qs('#add-tx-form-modal');
      if(addForm){
        addForm.addEventListener('submit', function(e){
          e.preventDefault();
          const fd = new FormData(addForm);
          if(!fd.get('action')) fd.append('action','add_tx');
          fetch(window.location.pathname, { method:'POST', headers: {'X-Requested-With':'XMLHttpRequest','X-CSRFToken': csrftoken}, body: fd })
            .then(r=>r.json()).then(json=>{
              if(json && json.ok){ hideModal('add-tx-modal'); window.location.reload(); }
              else { const err = qs('#add-modal-errors'); if(err){ err.style.display='block'; err.textContent = (json && json.errors)? (Array.isArray(json.errors)? json.errors.join('; '): JSON.stringify(json.errors)) : 'Failed to add transaction'; } }
            }).catch(err=>{ const errEl = qs('#add-modal-errors'); if(errEl){ errEl.style.display='block'; errEl.textContent = 'Network error'; } });
        });
      }

      // flatpickr init for consistency
      if(window.flatpickr){
        try{
          const fpOpts = { dateFormat: 'Y-m-d', allowInput: true };
          if(qs('#bulk_date')) { flatpickr('#bulk_date', fpOpts); console.debug('[transactions] flatpickr initialized #bulk_date'); }
          if(qs('#add-tx-date')) { flatpickr('#add-tx-date', fpOpts); console.debug('[transactions] flatpickr initialized #add-tx-date'); }
        }catch(e){ console.warn('flatpickr init failed', e); }
      }

      // Columns modal
      const columnsBtn = qs('#columns-btn'); if(columnsBtn) columnsBtn.addEventListener('click', ()=> showModal('columns-modal'));
      const columnsCancel = qs('#columns-cancel'); if(columnsCancel) columnsCancel.addEventListener('click', ()=> hideModal('columns-modal'));
      const columnsSave = qs('#columns-save');
      if(columnsSave){ columnsSave.addEventListener('click', function(){ const checked = Array.from(document.querySelectorAll('#columns-form input[name="columns"]:checked')).map(i=>i.value); fetch('/transactions/columns/', { method:'POST', headers: {'Content-Type':'application/json','X-CSRFToken': csrftoken}, body: JSON.stringify({columns: checked}) }).then(r=>r.json()).then(j=>{ if(j && j.ok){ hideModal('columns-modal'); window.location.reload(); } else { alert('Failed to save columns'); } }).catch(()=> alert('Network error')); }); }

      // Delete selected
      const delBtn = qs('#delete-selected');
      if(delBtn){ delBtn.addEventListener('click', function(){ const selected = rowCheckboxes().filter(cb=>cb.checked).map(cb=>cb.dataset.id); if(!selected.length) return; const delIds = qs('#delete-ids'); const delCount = qs('#delete-modal-count'); if(delIds) delIds.value = selected.join(','); if(delCount) delCount.textContent = selected.length + ' transactions will be deleted'; showModal('delete-modal'); }); }
      const delCancel = qs('#delete-cancel'); if(delCancel) delCancel.addEventListener('click', ()=> hideModal('delete-modal'));
      const delForm = qs('#delete-form');
      if(delForm){ delForm.addEventListener('submit', function(e){ e.preventDefault(); const ids = (qs('#delete-ids').value || '').split(',').map(s=>s.trim()).filter(Boolean); if(!ids.length) return hideModal('delete-modal'); Promise.all(ids.map(id=> fetch('/transactions/'+id+'/delete/', { method:'POST', headers:{ 'X-CSRFToken': csrftoken } }))).then(()=> window.location.reload()).catch(()=> { alert('Failed to delete'); window.location.reload(); }); }); }

      // Edit selected -> reuse bulk-edit modal
      const editBtn = qs('#edit-selected');
      if(editBtn){
        editBtn.addEventListener('click', function(){
          const selected = rowCheckboxes().filter(cb=>cb.checked).map(cb=>cb.dataset.id);
          if(!selected.length) return;
          const beIds = qs('#bulk-edit-ids'); const beCount = qs('#bulk-edit-count'); if(beIds) beIds.value = selected.join(','); if(beCount) beCount.textContent = selected.length + ' transactions selected';
          const form = qs('#bulk-edit-form'); if(!form) return;
          ['date','amount','description','direction','category','subcategory'].forEach(name=>{ const el = form.querySelector('[name="'+name+'"]'); if(el){ el.value = ''; const err = el.parentElement.querySelector('.field-error'); if(err) err.remove(); } });
          if(selected.length === 1){ const id = selected[0]; const cb = qs('.row-select[data-id="'+id+'"]'); if(cb){ if(form.querySelector('[name="date"]')) form.querySelector('[name="date"]').value = cb.dataset.date || ''; if(form.querySelector('[name="amount"]')) form.querySelector('[name="amount"]').value = cb.dataset.amount || ''; if(form.querySelector('[name="description"]')) form.querySelector('[name="description"]').value = cb.dataset.description || ''; if(form.querySelector('[name="direction"]')) form.querySelector('[name="direction"]').value = cb.dataset.direction || ''; if(form.querySelector('[name="category"]')) form.querySelector('[name="category"]').value = cb.dataset.category || ''; if(form.querySelector('[name="subcategory"]')) form.querySelector('[name="subcategory"]').value = cb.dataset.subcategory || ''; const title = qs('#bulk-edit-title'); if(title) title.textContent = 'Edit transaction'; } }
          else { const title = qs('#bulk-edit-title'); if(title) title.textContent = 'Bulk edit transactions'; }
          showModal('bulk-edit-modal');
        });
      }

      // AJAX submit for bulk-edit-form
      const bulkForm = qs('#bulk-edit-form');
      if(bulkForm){
        bulkForm.addEventListener('submit', function(e){ e.preventDefault(); const fd = new FormData(bulkForm); fetch(bulkForm.action, { method:'POST', headers: {'X-Requested-With':'XMLHttpRequest','X-CSRFToken': csrftoken }, body: fd }).then(r=> r.json()).then(json=>{ if(json && json.ok){ const updated = json.updated_ids || []; const applied = json.applied || {}; if(updated.length === 1){ const id = String(updated[0]); const cb = qs('.row-select[data-id="'+id+'"]'); if(cb){ const row = cb.closest('tr'); Object.keys(applied).forEach(function(k){ const v = applied[k]; if(['date','amount','direction','category','subcategory','description'].includes(k)){ if(k === 'date') cb.dataset.date = v; else if(k === 'amount') cb.dataset.amount = v; else if(k === 'direction') cb.dataset.direction = v; else if(k === 'category') cb.dataset.category = v; else if(k === 'subcategory') cb.dataset.subcategory = v; else if(k === 'description') cb.dataset.description = v; const td = row.querySelector('td[data-col="'+k+'"]'); if(td){ if(k === 'date'){ try{ const d = new Date(v); td.textContent = d.toLocaleDateString(undefined,{month:'short', day:'numeric', year:'numeric'}); }catch(e){ td.textContent = v; } } else { td.textContent = v; } } } }); } hideModal('bulk-edit-modal'); } else { window.location.reload(); } } else { if(json && json.errors){ Object.keys(json.errors).forEach(function(field){ const input = bulkForm.querySelector('[name="'+field+'"]'); if(input){ let el = input.parentElement.querySelector('.field-error'); if(!el){ el = document.createElement('div'); el.className = 'field-error'; input.parentElement.appendChild(el); } el.textContent = Array.isArray(json.errors[field])? json.errors[field].join('; '): String(json.errors[field]); } }); } else { alert('Failed to apply changes'); } } }).catch(err=>{ alert('Network error'); console.error(err); }); });
        const bulkCancel = qs('#bulk-edit-cancel'); if(bulkCancel) bulkCancel.addEventListener('click', ()=> hideModal('bulk-edit-modal'));
      }

      console.debug('[transactions] init end');
    }catch(err){ console.error('transactions.init fatal error', err); }
  }

  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();

})();
