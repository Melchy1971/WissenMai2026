import React from 'react';
import { useAnalysis } from '../features/analysis/useAnalysis.js';
import { AnalysisJobList } from '../features/analysis/AnalysisJobList.jsx';
import { AnalysisJobDetail } from '../features/analysis/AnalysisJobDetail.jsx';
import { NewAnalysisJobDialog } from '../features/analysis/NewAnalysisJobDialog.jsx';

var PAGE_STYLE = {
  display: 'flex',
  flexDirection: 'column',
  height: '100%',
  overflow: 'hidden',
};

var HEADER_STYLE = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  padding: '16px 24px',
  borderBottom: '1px solid var(--color-border)',
  flexShrink: 0,
  background: 'var(--color-surface)',
};

var CONTENT_STYLE = {
  display: 'flex',
  flex: 1,
  gap: '12px',
  padding: '12px 24px 24px',
  overflow: 'hidden',
  minHeight: 0,
};

var BTN_PRIMARY_STYLE = {
  border: 'none',
  borderRadius: 'var(--radius-md)',
  padding: '8px 16px',
  fontSize: '13px',
  fontWeight: 600,
  cursor: 'pointer',
  background: 'var(--t-magenta)',
  color: '#fff',
  display: 'flex',
  alignItems: 'center',
  gap: '6px',
};

export function AnalysisPage() {
  var analysis = useAnalysis();

  return (
    <div style={PAGE_STYLE} data-testid="analysis-page">
      <div style={HEADER_STYLE}>
        <div>
          <h1 style={{ margin: 0, fontSize: '18px', fontWeight: 700, color: 'var(--color-text)' }}>
            Analysen
          </h1>
          <p style={{ margin: 0, fontSize: '12px', color: 'var(--color-text-tertiary)', marginTop: '2px' }}>
            KI-gestutzte Analyse von Wissensbasis-Inhalten
          </p>
        </div>
        <button
          style={BTN_PRIMARY_STYLE}
          data-testid="btn-new-analysis"
          onClick={analysis.openNewJobDialog}
        >
          <span>+</span>
          Neue Analyse
        </button>
      </div>

      <div style={CONTENT_STYLE}>
        <AnalysisJobList
          listState={analysis.listState}
          selectedId={analysis.selectedId}
          statusFilter={analysis.statusFilter}
          page={analysis.page}
          onSelect={analysis.handleSelect}
          onRefresh={analysis.handleRefresh}
          onNewJob={analysis.openNewJobDialog}
          onFilterChange={analysis.handleFilterChange}
          onPageChange={analysis.setPage}
        />
        <AnalysisJobDetail
          detailState={analysis.detailState}
          actionState={analysis.actionState}
          onCancel={analysis.handleCancel}
          onRetry={analysis.handleRetry}
          onMarkForReview={analysis.handleMarkForReview}
          onApprove={analysis.handleApprove}
          onReject={analysis.handleReject}
          onImport={analysis.handleImport}
        />
      </div>

      <NewAnalysisJobDialog
        open={analysis.newJobDialogOpen}
        onClose={analysis.closeNewJobDialog}
        onJobCreated={analysis.handleJobCreated}
      />
    </div>
  );
}
