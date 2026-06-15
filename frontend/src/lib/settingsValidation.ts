function add(errors, field, message) {
  errors[field] = message;
}

function numberInRange(errors, section, key, value, min, max) {
  if (value === undefined || value === null || value === '') return;
  const n = Number(value);
  if (!Number.isFinite(n) || n < min || n > max) {
    add(errors, `${section}.${key}`, `${min}-${max}`);
  }
}

export function diffSettingsSection(original = {}, current = {}) {
  const diff = {};
  Object.entries(current || {}).forEach(([key, value]) => {
    if (JSON.stringify(original?.[key]) !== JSON.stringify(value)) {
      diff[key] = value;
    }
  });
  return diff;
}

export function validateSettingsPatch(allSettings, patch, { isAdmin = false } = {}) {
  const errors = {};
  const next = JSON.parse(JSON.stringify(allSettings || {}));
  Object.entries(patch || {}).forEach(([section, values]) => {
    next[section] = { ...(next[section] || {}), ...(values || {}) };
  });

  Object.entries(patch || {}).forEach(([section, values]) => {
    Object.entries(values || {}).forEach(([key, value]) => {
      if (section === 'provider') {
        if (key === 'timeout_seconds') numberInRange(errors, section, key, value, 1, 300);
        if (key === 'max_retries') numberInRange(errors, section, key, value, 0, 5);
      }
      if (section === 'rag') {
        if (key === 'chunk_size') numberInRange(errors, section, key, value, 100, 2000);
        if (key === 'chunk_overlap') numberInRange(errors, section, key, value, 0, 1999);
        if (key === 'min_score') numberInRange(errors, section, key, value, 0, 1);
        if (key === 'max_chunks') numberInRange(errors, section, key, value, 1, 20);
      }
      if (section === 'agents') {
        if (key === 'max_steps') numberInRange(errors, section, key, value, 1, 100);
        if (key === 'max_tool_calls') numberInRange(errors, section, key, value, 0, 50);
        if (key === 'max_runtime_seconds') numberInRange(errors, section, key, value, 1, 3600);
      }
      if (section === 'collaboration') {
        if (key === 'max_agents') numberInRange(errors, section, key, value, 1, 10);
        if (key === 'revision_cycles') numberInRange(errors, section, key, value, 0, 10);
      }
      if (section === 'governance' && key === 'approval_expiry_minutes') {
        numberInRange(errors, section, key, value, 1, 1440);
      }
      if (section === 'memory') {
        if (key === 'max_entries') numberInRange(errors, section, key, value, 1, 100000);
        if (key === 'decay_rate') numberInRange(errors, section, key, value, 0, 1);
      }
    });
  });

  if (Number(next.rag?.chunk_overlap) >= Number(next.rag?.chunk_size)) {
    add(errors, 'rag.chunk_overlap', 'Overlap muss kleiner als Chunkgroesse sein.');
  }
  if (next.security?.source_required === false && !isAdmin) {
    add(errors, 'security.source_required', 'Nur Admins duerfen diese Pflicht deaktivieren.');
  }
  if (next.memory?.memory_extraction_enabled && next.security?.review_queue_required === false) {
    add(errors, 'security.review_queue_required', 'Bei aktiver Memory Extraction erforderlich.');
  }
  if (next.agents?.agents_enabled && next.security?.validation_pipeline_enabled === false) {
    add(errors, 'security.validation_pipeline_enabled', 'Bei aktiven Agenten erforderlich.');
  }
  if (next.collaboration?.collaboration_enabled && next.collaboration?.arbitration_enabled === false) {
    add(errors, 'collaboration.arbitration_enabled', 'Bei aktiver Collaboration erforderlich.');
  }
  if (next.governance?.changesets_enabled && next.security?.rollback_enabled === false) {
    add(errors, 'security.rollback_enabled', 'Bei aktiven ChangeSets erforderlich.');
  }
  if (next.security?.plugins_enabled && next.security?.plugin_sandbox_enabled === false) {
    add(errors, 'security.plugin_sandbox_enabled', 'Bei aktiven Plugins erforderlich.');
  }
  return errors;
}
