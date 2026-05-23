document.addEventListener('DOMContentLoaded', () => {
  // 1. Sidebar Search Filter
  const sidebarSearch = document.getElementById('sidebar-search-input');
  if (sidebarSearch) {
    sidebarSearch.addEventListener('input', (e) => {
      const query = e.target.value.toLowerCase().strip ? e.target.value.toLowerCase().trim() : e.target.value.toLowerCase();
      const dbItems = document.querySelectorAll('details.db-item');
      
      dbItems.forEach(dbItem => {
        const dbName = dbItem.querySelector('summary.db-summary').textContent.toLowerCase();
        const tables = dbItem.querySelectorAll('.table-item');
        let dbMatch = dbName.includes(query);
        let tableMatchCount = 0;
        
        tables.forEach(table => {
          const tableName = table.textContent.toLowerCase();
          if (tableName.includes(query)) {
            table.style.display = 'flex';
            tableMatchCount++;
          } else {
            table.style.display = 'none';
          }
        });
        
        if (dbMatch || tableMatchCount > 0) {
          dbItem.style.display = 'block';
          if (query !== '') {
            dbItem.open = true; // Auto expand if matching search
          }
        } else {
          dbItem.style.display = 'none';
        }
      });
    });
  }

  // 2. Alert Dismissal Timer
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(alert => {
    setTimeout(() => {
      alert.style.opacity = '0';
      alert.style.transition = 'opacity 0.6s ease';
      setTimeout(() => alert.remove(), 600);
    }, 4500);
  });

  // 3. SQL Editor Actions (History, Helpers)
  const sqlTextarea = document.getElementById('sql-query-textarea');
  if (sqlTextarea) {
    // Inject clicked table/column into editor
    const insertIntoEditor = (text) => {
      const start = sqlTextarea.selectionStart;
      const end = sqlTextarea.selectionEnd;
      const currentVal = sqlTextarea.value;
      sqlTextarea.value = currentVal.substring(0, start) + text + currentVal.substring(end);
      sqlTextarea.focus();
      sqlTextarea.selectionStart = sqlTextarea.selectionEnd = start + text.length;
    };

    document.querySelectorAll('.sql-helper-tbl').forEach(tbl => {
      tbl.addEventListener('click', () => {
        insertIntoEditor(`\`${tbl.dataset.name}\``);
      });
    });

    document.querySelectorAll('.sql-helper-col').forEach(col => {
      col.addEventListener('click', () => {
        insertIntoEditor(`\`${col.dataset.name}\``);
      });
    });

    // Query template generators
    const activeTable = sqlTextarea.dataset.activeTable;
    const generateBtn = document.getElementById('btn-gen-select');
    if (generateBtn && activeTable) {
      document.getElementById('btn-gen-select').addEventListener('click', () => {
        sqlTextarea.value = `SELECT * FROM \`${activeTable}\` WHERE 1;`;
      });
      document.getElementById('btn-gen-insert').addEventListener('click', () => {
        sqlTextarea.value = `INSERT INTO \`${activeTable}\` (\n  /* columns */\n) VALUES (\n  /* values */\n);`;
      });
      document.getElementById('btn-gen-update').addEventListener('click', () => {
        sqlTextarea.value = `UPDATE \`${activeTable}\` SET \`col\` = 'val' WHERE \`id\` = 1;`;
      });
      document.getElementById('btn-gen-delete').addEventListener('click', () => {
        sqlTextarea.value = `DELETE FROM \`${activeTable}\` WHERE \`id\` = 1;`;
      });
    }

    // LocalStorage SQL Query History
    const loadHistory = () => {
      const historyList = document.getElementById('sql-history-list');
      if (!historyList) return;
      
      const history = JSON.parse(localStorage.getItem('pysql_history') || '[]');
      historyList.innerHTML = '';
      
      if (history.length === 0) {
        historyList.innerHTML = '<div class="text-sub font-size-sm">No recent queries.</div>';
        return;
      }
      
      history.forEach((q, idx) => {
        const item = document.createElement('div');
        item.className = 'sql-history-item';
        item.style.padding = '8px 12px';
        item.style.borderBottom = '1px solid var(--panel-border)';
        item.style.cursor = 'pointer';
        item.style.fontSize = '0.85rem';
        item.style.fontFamily = 'var(--font-mono)';
        item.style.whiteSpace = 'nowrap';
        item.style.overflow = 'hidden';
        item.style.textOverflow = 'ellipsis';
        item.textContent = q;
        item.title = q;
        
        item.addEventListener('click', () => {
          sqlTextarea.value = q;
        });
        
        historyList.appendChild(item);
      });
    };

    // HTML escaping helper for safe data rendering
    const escapeHtml = (str) => {
      if (str === null || str === undefined) return '';
      return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
    };

    // Save query on submit and execute via AJAX
    const sqlForm = document.getElementById('sql-console-form');
    const resultsContainer = document.getElementById('sql-results-container');

    if (sqlForm && resultsContainer) {
      sqlForm.addEventListener('submit', (e) => {
        e.preventDefault(); // Prevent standard page reload
        
        const query = sqlTextarea.value.trim();
        if (!query) return;
        
        // Save to query history
        let history = JSON.parse(localStorage.getItem('pysql_history') || '[]');
        history = history.filter(h => h !== query);
        history.unshift(query);
        if (history.length > 20) history.pop();
        localStorage.setItem('pysql_history', JSON.stringify(history));
        loadHistory();
        
        // Show loading state
        const submitBtn = sqlForm.querySelector('button[type="submit"]');
        const originalBtnHTML = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '⏳ Executing...';
        
        resultsContainer.innerHTML = `
          <div class="glass-card" style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 40px; min-height: 200px;">
            <div class="spinner" style="border: 4px solid rgba(255,255,255,0.1); border-top: 4px solid #3b82f6; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin-bottom: 16px;"></div>
            <p style="color: var(--text-muted); font-size: 0.95rem;">Executing query statements sequentially...</p>
          </div>
          <style>
            @keyframes spin {
              0% { transform: rotate(0deg); }
              100% { transform: rotate(360deg); }
            }
          </style>
        `;
        
        // Prepare Form Data
        const formData = new FormData(sqlForm);
        
        // Make the AJAX request
        fetch(sqlForm.action, {
          method: 'POST',
          headers: {
            'X-Requested-With': 'XMLHttpRequest'
          },
          body: formData
        })
        .then(response => {
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }
          return response.json();
        })
        .then(data => {
          // Re-enable button
          submitBtn.disabled = false;
          submitBtn.innerHTML = originalBtnHTML;
          
          if (!data.results || data.results.length === 0) {
            resultsContainer.innerHTML = '';
            return;
          }
          
          // Build results HTML
          let html = `
            <div class="glass-card">
              <div class="glass-card-header">
                <h2>📊 Execution Results</h2>
              </div>
          `;
          
          data.results.forEach(res => {
            const statusClass = res.success ? 'success' : 'danger';
            html += `
              <div class="sql-log-item ${statusClass}">
                <div class="sql-statement">${escapeHtml(res.query)}</div>
                <div class="sql-log-meta">
            `;
            
            if (res.success) {
              html += `<span style="color: var(--success); font-weight: 600;">✔️ Success</span>`;
              if (res.affected_rows !== null && res.affected_rows !== undefined) {
                html += ` | Affected rows: <strong>${res.affected_rows}</strong>`;
              }
              if (res.last_row_id > 0) {
                html += ` | Last insert ID: <strong>${res.last_row_id}</strong>`;
              }
              if (res.warning_count > 0) {
                html += ` | Warnings: <strong style="color: var(--warning)">${res.warning_count}</strong>`;
              }
            } else {
              html += `<span style="color: var(--danger); font-weight: 600;">❌ Error</span>: ${escapeHtml(res.error)}`;
            }
            
            html += `
                </div>
            `;
            
            // Render rows if returned
            if (res.success && res.rows && res.rows.length > 0) {
              html += `
                <div class="table-container" style="margin-top: 16px; max-height: 400px; overflow-y: auto;">
                  <table class="custom-table" aria-label="Query result set">
                    <thead>
                      <tr>
              `;
              
              res.columns.forEach(col => {
                html += `<th>${escapeHtml(col)}</th>`;
              });
              
              html += `
                      </tr>
                    </thead>
                    <tbody>
              `;
              
              res.rows.forEach(row => {
                html += `<tr>`;
                res.columns.forEach(col => {
                  const val = row[col];
                  if (val === null || val === undefined) {
                    html += `<td><span class="tag" style="font-style: italic;">NULL</span></td>`;
                  } else {
                    html += `<td>${escapeHtml(val)}</td>`;
                  }
                });
                html += `</tr>`;
              });
              
              html += `
                    </tbody>
                  </table>
                </div>
              `;
            } else if (res.success && res.columns && res.columns.length > 0) {
              // Handle empty result sets for queries like SHOW or SELECT returning 0 rows
              html += `
                <div style="margin-top: 12px; font-style: italic; color: var(--text-muted); font-size: 0.95rem;">
                  Empty set (query returned 0 rows).
                </div>
              `;
            }
            
            html += `</div>`;
          });
          
          html += `</div>`;
          resultsContainer.innerHTML = html;
        })
        .catch(err => {
          submitBtn.disabled = false;
          submitBtn.innerHTML = originalBtnHTML;
          resultsContainer.innerHTML = `
            <div class="glass-card" style="border-left: 4px solid var(--danger);">
              <div class="glass-card-header">
                <h2>❌ Query Execution Failed</h2>
              </div>
              <div style="padding: 16px; color: var(--danger);">
                Failed to communicate with database server. Detail: ${escapeHtml(err.message)}
              </div>
            </div>
          `;
        });
      });
    }

    loadHistory();

    const clearHistoryBtn = document.getElementById('clear-history-btn');
    if (clearHistoryBtn) {
      clearHistoryBtn.addEventListener('click', () => {
        localStorage.removeItem('pysql_history');
        loadHistory();
      });
    }
  }

  // 4. Dynamic Column adding in Table Create Form
  const addFieldBtn = document.getElementById('add-field-row-btn');
  const schemaContainer = document.getElementById('schema-fields-container');
  if (addFieldBtn && schemaContainer) {
    let fieldCount = parseInt(addFieldBtn.dataset.count);
    
    addFieldBtn.addEventListener('click', () => {
      const newRow = document.createElement('div');
      newRow.className = 'schema-column-row';
      newRow.innerHTML = `
        <div>
          <input type="text" name="field_name_${fieldCount}" placeholder="Column Name" class="form-control" required autocomplete="off">
        </div>
        <div>
          <select name="field_type_${fieldCount}" class="form-control">
            <option value="INT">INT</option>
            <option value="VARCHAR">VARCHAR</option>
            <option value="TEXT">TEXT</option>
            <option value="DATE">DATE</option>
            <option value="DATETIME">DATETIME</option>
            <option value="TIMESTAMP">TIMESTAMP</option>
            <option value="DECIMAL">DECIMAL</option>
            <option value="TINYINT">TINYINT</option>
            <option value="DOUBLE">DOUBLE</option>
            <option value="BOOLEAN">BOOLEAN</option>
          </select>
        </div>
        <div>
          <input type="text" name="field_length_${fieldCount}" placeholder="Length" class="form-control" autocomplete="off">
        </div>
        <div>
          <select name="field_default_${fieldCount}" class="form-control default-select" data-index="${fieldCount}">
            <option value="NONE">None</option>
            <option value="USER_DEFINED">As defined:</option>
            <option value="NULL">NULL</option>
            <option value="CURRENT_TIMESTAMP">CURRENT_TIMESTAMP</option>
          </select>
        </div>
        <div>
          <input type="text" name="field_default_value_${fieldCount}" id="default_val_${fieldCount}" placeholder="Value" class="form-control" disabled autocomplete="off">
        </div>
        <div>
          <select name="field_collation_${fieldCount}" class="form-control">
            <option value="utf8mb4_general_ci">utf8mb4_general_ci</option>
            <option value="utf8mb4_unicode_ci">utf8mb4_unicode_ci</option>
            <option value="utf8_general_ci">utf8_general_ci</option>
          </select>
        </div>
        <div>
          <select name="field_attribute_${fieldCount}" class="form-control">
            <option value="">--</option>
            <option value="UNSIGNED">UNSIGNED</option>
            <option value="ON UPDATE CURRENT_TIMESTAMP">ON UPDATE CURRENT_TIMESTAMP</option>
          </select>
        </div>
        <div style="display: flex; gap: 8px; justify-content: center; align-items: center;">
          <input type="checkbox" name="field_null_${fieldCount}"> Null
          <select name="field_index_${fieldCount}" class="form-control" style="width: 80px; padding: 4px;">
            <option value="">None</option>
            <option value="PRIMARY">PRIMARY</option>
            <option value="UNIQUE">UNIQUE</option>
            <option value="INDEX">INDEX</option>
          </select>
          <input type="checkbox" name="field_ai_${fieldCount}"> A_I
        </div>
      `;
      
      schemaContainer.appendChild(newRow);
      
      // Wire up the new default dropdown change listener
      const newSelect = newRow.querySelector('.default-select');
      newSelect.addEventListener('change', (e) => {
        const idx = e.target.dataset.index;
        const valInput = document.getElementById(`default_val_${idx}`);
        if (e.target.value === 'USER_DEFINED') {
          valInput.disabled = false;
          valInput.focus();
        } else {
          valInput.value = '';
          valInput.disabled = true;
        }
      });
      
      fieldCount++;
      addFieldBtn.dataset.count = fieldCount;
      document.getElementById('num-fields-hidden').value = fieldCount;
    });
  }

  // 5. Toggle default values inputs across page load elements
  document.querySelectorAll('.default-select').forEach(select => {
    select.addEventListener('change', (e) => {
      const idx = e.target.dataset.index;
      const valInput = document.getElementById(`default_val_${idx}`);
      if (e.target.value === 'USER_DEFINED') {
        valInput.disabled = false;
        valInput.focus();
      } else {
        valInput.value = '';
        valInput.disabled = true;
      }
    });
  });

  // 6. Delete confirmations dialogs
  document.querySelectorAll('.btn-confirm-delete').forEach(btn => {
    btn.addEventListener('click', (e) => {
      if (!confirm("Are you absolutely sure you want to perform this delete/drop operation? This cannot be undone.")) {
        e.preventDefault();
      }
    });
  });

  // 7. Multi-row checkbox selections
  const checkAll = document.getElementById('check-all-rows');
  if (checkAll) {
    const rowChecks = document.querySelectorAll('.row-checkbox');
    checkAll.addEventListener('change', (e) => {
      rowChecks.forEach(cb => {
        cb.checked = e.target.checked;
      });
    });
  }
});
