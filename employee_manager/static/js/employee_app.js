document.addEventListener('DOMContentLoaded', () => {
  // 1. Auto dismiss alerts after a delay
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(alert => {
    setTimeout(() => {
      alert.style.opacity = '0';
      alert.style.transition = 'opacity 0.6s ease';
      setTimeout(() => alert.remove(), 600);
    }, 4500);
  });

  // 2. Interactive delete prompts
  const deleteForms = document.querySelectorAll('.delete-form, .btn-confirm-delete');
  deleteForms.forEach(elem => {
    const trigger = elem.tagName === 'FORM' ? elem : elem.closest('form');
    if (trigger) {
      trigger.addEventListener('submit', (e) => {
        if (!confirm("Are you absolutely sure you want to delete this record? This action cannot be undone and may clear associated relationships.")) {
          e.preventDefault();
        }
      });
    }
  });

  // 3. Project timeline dates check
  const projectForm = document.getElementById('project-form');
  if (projectForm) {
    projectForm.addEventListener('submit', (e) => {
      const startDateVal = document.getElementById('start_date').value;
      const endDateVal = document.getElementById('end_date').value;
      
      if (startDateVal && endDateVal) {
        const start = new Date(startDateVal);
        const end = new Date(endDateVal);
        
        if (end < start) {
          e.preventDefault();
          alert("Error: The project end date cannot be earlier than its start date.");
        }
      }
    });
  }

  // 4. Quick Table Client Search Filter (Dynamic)
  const quickSearch = document.getElementById('employee-quick-search');
  if (quickSearch) {
    quickSearch.addEventListener('input', (e) => {
      const query = e.target.value.toLowerCase().strip ? e.target.value.toLowerCase().trim() : e.target.value.toLowerCase();
      const rows = document.querySelectorAll('.custom-table tbody tr');
      
      rows.forEach(row => {
        const cells = Array.from(row.querySelectorAll('td'));
        // Exclude actions column (first or last)
        const content = cells.slice(1).map(c => c.textContent.toLowerCase()).join(' ');
        
        if (content.includes(query)) {
          row.style.display = '';
        } else {
          row.style.display = 'none';
        }
      });
    });
  }
});
