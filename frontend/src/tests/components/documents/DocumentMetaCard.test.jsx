import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { DocumentMetaCard } from '../../../components/documents/DocumentMetaCard.jsx';

const baseDocument = {
  title: 'Testdokument',
  lifecycleStatus: { label: 'Aktiv', value: 'active' },
  importStatus: { label: 'Verarbeitet', value: 'parsed' },
  sourceType: 'upload',
  mimeType: 'application/pdf',
  parserVersion: '2.1.0',
  ocrUsed: false,
  versions: [{}],
  chunkCount: 42,
  totalChars: 18000,
  archivedAtLabel: null,
  createdAtLabel: '01.06.2026',
  updatedAtLabel: '10.06.2026',
};

describe('DocumentMetaCard — keine technischen IDs', () => {
  it('zeigt keine technischen UUID-Felder an', () => {
    const documentWithIds = {
      ...baseDocument,
      id: 'uuid-1234-5678-abcd',
      workspaceId: 'ws-uuid-9876',
      ownerUserId: 'user-uuid-5555',
    };

    const { container } = render(<DocumentMetaCard document={documentWithIds} />);
    const text = container.textContent;

    // Technische IDs dürfen nicht als sichtbarer Text erscheinen
    expect(text).not.toContain('uuid-1234-5678-abcd');
    expect(text).not.toContain('ws-uuid-9876');
    expect(text).not.toContain('user-uuid-5555');

    // Keine technischen Feldbezeichnungen
    expect(text).not.toContain('ID');
    expect(text).not.toContain('Workspace');
    expect(text).not.toContain('Owner');
  });

  it('zeigt fachliche Pflichtfelder an', () => {
    render(<DocumentMetaCard document={baseDocument} />);

    expect(screen.getByRole('heading', { level: 2, name: 'Testdokument' })).toBeInTheDocument();
    expect(screen.getByText('Importquelle')).toBeInTheDocument();
    expect(screen.getByText('upload')).toBeInTheDocument();
    expect(screen.getByText('Dateityp')).toBeInTheDocument();
    expect(screen.getByText('application/pdf')).toBeInTheDocument();
    expect(screen.getByText('Erstellt')).toBeInTheDocument();
    expect(screen.getByText('01.06.2026')).toBeInTheDocument();
    expect(screen.getByText('Aktualisiert')).toBeInTheDocument();
  });

  it('zeigt Tags an wenn vorhanden', () => {
    const documentWithTags = {
      ...baseDocument,
      tags: [{ name: 'Compliance' }, { name: 'DSGVO' }],
    };

    render(<DocumentMetaCard document={documentWithTags} />);

    expect(screen.getByText('Tags')).toBeInTheDocument();
    expect(screen.getByText('Compliance, DSGVO')).toBeInTheDocument();
  });

  it('zeigt kein Tags-Feld wenn keine Tags vorhanden', () => {
    const documentWithoutTags = { ...baseDocument, tags: [] };

    render(<DocumentMetaCard document={documentWithoutTags} />);

    expect(screen.queryByText('Tags')).not.toBeInTheDocument();
  });

  it('zeigt keine technischen IDs auch ohne id/workspaceId/ownerUserId-Props', () => {
    render(<DocumentMetaCard document={baseDocument} />);

    const { container } = render(<DocumentMetaCard document={baseDocument} />);
    const dtElements = container.querySelectorAll('dt');
    const dtTexts = Array.from(dtElements).map(el => el.textContent);

    expect(dtTexts).not.toContain('ID');
    expect(dtTexts).not.toContain('Workspace');
    expect(dtTexts).not.toContain('Owner');
  });
});
