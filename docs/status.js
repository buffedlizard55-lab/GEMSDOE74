(() => {
  const statusLabel = document.getElementById('status-label');
  const statusDetail = document.getElementById('status-detail');
  const disabledDownload = document.getElementById('disabled-download');
  const readyDownload = document.getElementById('ready-download');
  const submissionName = document.getElementById('submission-name');
  const submissionNote = document.getElementById('submission-note');
  if (!statusLabel || !statusDetail || !disabledDownload || !readyDownload) return;

  fetch('./data/readiness.json', { cache: 'no-store' })
    .then((response) => {
      if (!response.ok) throw new Error('Readiness file not available');
      return response.json();
    })
    .then((report) => {
      const localTif = typeof report.download_url === 'string'
        && report.download_url.startsWith('./downloads/')
        && report.download_url.endsWith('.tif');
      const hasNoBlockers = Array.isArray(report.blockers) && report.blockers.length === 0;
      const hasSubmissionDetails = typeof report.submission_name === 'string'
        && typeof report.submission_note === 'string'
        && report.submission_note.trim().length <= 140;
      if (report.schema_version !== 'gemsdoe74-readiness-v1'
        || report.status !== 'READY'
        || report.download_enabled !== true
        || !localTif
        || !hasNoBlockers
        || !hasSubmissionDetails) return;

      statusLabel.textContent = 'READY TO SUBMIT';
      statusLabel.style.color = 'var(--green)';
      const statusCard = statusLabel.closest('.status-card');
      if (statusCard) statusCard.style.borderTopColor = 'var(--green)';
      statusDetail.textContent = 'The validated artifact, writer receipt, holdout evidence, and uniqueness checks are recorded in the readiness manifest. Review the receipt before uploading.';
      disabledDownload.hidden = true;
      readyDownload.href = report.download_url;
      if (typeof report.submission_name === 'string') {
        readyDownload.download = report.download_url.split('/').pop();
        readyDownload.setAttribute('aria-label', `Download the validated GeoTIFF for ${report.submission_name}`);
      }
      readyDownload.style.display = 'block';
      if (submissionName && typeof report.submission_name === 'string') {
        submissionName.textContent = report.submission_name;
      }
      if (submissionNote && typeof report.submission_note === 'string') {
        submissionNote.textContent = report.submission_note;
      }
    })
    .catch(() => {
      // Safe fallback is the static BLOCKED state already present in index.html.
    });
})();
