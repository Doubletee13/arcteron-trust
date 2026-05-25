/**
 * Reusable Receipt Modal Component
 * Provides a consistent receipt modal across all dashboard pages
 * Updated layout: OPay-style card, unified data source, Image/PDF share options
 */

const ReceiptModal = (function () {
    let modalElement = null;
    let isInitialized = false;
    let currentTransactionId = null;
    let currentReceiptData = null;

    /**
     * Mask account number
     */
    function maskAccountNumber(accountNumber) {
        if (!accountNumber || accountNumber === '—') return '—';
        const str = String(accountNumber).replace(/\D/g, '');
        if (str.length <= 4) return (str.length > 0) ? '**** ' + str.padStart(4, '0') : '—';
        return '**** ' + str.slice(-4);
    }

    /**
     * Format full account number
     */
    function formatFullAccountNumber(accountNumber) {
        if (!accountNumber || accountNumber === '—') return '—';
        const str = String(accountNumber).replace(/\D/g, '');
        if (str.length <= 4) return str.padEnd(4, '0');
        const groups = [];
        for (let i = 0; i < str.length; i += 4) {
            groups.push(str.slice(i, i + 4));
        }
        return groups.join(' ');
    }

    function init() {
        if (isInitialized) return;

        const modalHTML = `
            <div class="rcp-overlay" id="receiptModal" onclick="if(event.target===this) ReceiptModal.close()">
                <div class="rcp-modal" id="receiptModalCard">
                    <!-- The capture area for html2canvas -->
                    <div id="receiptCaptureArea" class="rcp-capture-area">
                        <!-- Watermark generated via CSS ::before -->
                        <div class="rcp-header">
                            <div class="rcp-logo-wrap">
                                <svg width="24" height="24" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
                                    <circle cx="20" cy="20" r="18" stroke="currentColor" stroke-width="2" opacity="0.4" />
                                    <path d="M20 8 L30 28 H24 L20 20 L16 28 H10 Z" fill="currentColor" opacity="0.9" />
                                    <path d="M14 23 H26" stroke="currentColor" stroke-width="2" opacity="0.8" />
                                    <circle cx="20" cy="6" r="2" fill="currentColor" opacity="0.6" />
                                </svg>
                                <span>Arcteron Trust</span>
                            </div>
                            <div class="rcp-header-label">Transaction Receipt</div>
                            <button class="rcp-close-btn" id="rcpCloseBtn">&times;</button>
                        </div>

                        <div class="rcp-body">
                            <div class="rcp-amount-section">
                                <div class="rcp-amount" id="rcpAmount">$0.00</div>
                                <div class="rcp-status" id="rcpStatus">Completed</div>
                                <div class="rcp-datetime" id="rcpDateTime">May 23, 2026 · 08:37:54 AM UTC</div>
                            </div>

                            <div class="rcp-divider"></div>

                            <div class="rcp-info-list">
                                <div class="rcp-row">
                                    <div class="rcp-label" id="rcpPartyLabel">Transfer To</div>
                                    <div class="rcp-value" id="rcpParty">External Sender</div>
                                </div>
                                <div class="rcp-row">
                                    <div class="rcp-label">Bank</div>
                                    <div class="rcp-value" id="rcpBank">Arcteron Trust</div>
                                </div>
                                <div class="rcp-row">
                                    <div class="rcp-label">Account No.</div>
                                    <div class="rcp-value" id="rcpRecipientAcct">**** 0000</div>
                                </div>
                                <div class="rcp-row">
                                    <div class="rcp-label">Reference</div>
                                    <div class="rcp-value" id="rcpRef">#0000</div>
                                </div>
                                <div class="rcp-row">
                                    <div class="rcp-label">Type</div>
                                    <div class="rcp-value" id="rcpType">Transfer</div>
                                </div>
                                <div class="rcp-row">
                                    <div class="rcp-label">Description</div>
                                    <div class="rcp-value" id="rcpDescription">—</div>
                                </div>
                                <div class="rcp-row">
                                    <div class="rcp-label">Your Account</div>
                                    <div class="rcp-value" id="rcpAccount">**** 0000</div>
                                </div>
                            </div>

                            <div class="rcp-divider"></div>

                            <div class="rcp-footer-tagline">
                                This is an official transaction receipt issued by Arcteron Trust — Private Banking &amp; Wealth Management. FDIC Insured &bull; Member SIPC.
                                <br><br>
                                © <span id="rcpYear">2026</span> Arcteron Trust
                            </div>
                        </div>
                    </div>

                    <!-- Action Buttons -->
                    <div class="rcp-actions">
                        <button class="rcp-btn rcp-btn-secondary" onclick="ReceiptModal.shareAsImage()" id="btnShareImg">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                                <circle cx="8.5" cy="8.5" r="1.5"></circle>
                                <polyline points="21 15 16 10 5 21"></polyline>
                            </svg>
                            Share Image
                        </button>
                        <button class="rcp-btn rcp-btn-primary" onclick="ReceiptModal.downloadReceipt()">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                                <polyline points="7 10 12 15 17 10" />
                                <line x1="12" y1="15" x2="12" y2="3" />
                            </svg>
                            Share PDF
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);
        modalElement = document.getElementById('receiptModal');
        document.getElementById('rcpYear').textContent = new Date().getFullYear();
        document.getElementById('rcpCloseBtn').addEventListener('click', ReceiptModal.close); // Directly call ReceiptModal.close
        isInitialized = true;

        addStyles();
    }

    function addStyles() {
        if (document.getElementById('rcp-styles')) return;

        const style = document.createElement('style');
        style.id = 'rcp-styles';
        style.textContent = `
            /* Global Overlay */
            .rcp-overlay {
                display: none;
                position: fixed;
                inset: 0;
                background: rgba(0, 0, 0, 0.65);
                backdrop-filter: blur(5px);
                z-index: 9999;
                align-items: center;
                justify-content: center;
                opacity: 0;
                transition: opacity 0.3s ease;
            }
            .rcp-overlay.show {
                display: flex;
                opacity: 1;
            }

            /* Main Card Container */
            .rcp-modal {
                width: 92%;
                max-width: 440px;
                display: flex;
                flex-direction: column;
                gap: 16px;
                transform: translateY(20px);
                transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            }
            .rcp-overlay.show .rcp-modal {
                transform: translateY(0);
            }

            /* Capture Area (The actual receipt) */
            .rcp-capture-area {
                background: var(--bg-secondary, #1F2937);
                border-radius: 16px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                overflow: hidden;
                position: relative;
                color: var(--text-primary, #F9FAFB);
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            }

            [data-theme="light"] .rcp-capture-area {
                background: #FFFFFF;
                color: #111827;
                box-shadow: 0 10px 30px rgba(0,0,0,0.08);
            }

            /* Checkered SVG Watermark */
            .rcp-capture-area::before {
                content: '';
                position: absolute;
                inset: 0;
                opacity: 0.035;
                pointer-events: none;
                z-index: 0;
                background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='100' viewBox='0 0 120 100'%3E%3Cg transform='rotate(-25 60 50)'%3E%3Ccircle cx='20' cy='20' r='18' stroke='%23ffffff' stroke-width='1.5' fill='none'/%3E%3Cpath d='M20 8 L30 28 H24 L20 20 L16 28 H10 Z' fill='%23ffffff'/%3E%3Ctext x='45' y='24' font-family='Times New Roman' font-weight='bold' font-size='14' fill='%23ffffff'%3EArcteron Trust%3C/text%3E%3C/g%3E%3C/svg%3E");
                background-size: 160px 130px;
                background-repeat: repeat;
            }
            [data-theme="light"] .rcp-capture-area::before {
                background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='100' viewBox='0 0 120 100'%3E%3Cg transform='rotate(-25 60 50)'%3E%3Ccircle cx='20' cy='20' r='18' stroke='%23000000' stroke-width='1.5' fill='none'/%3E%3Cpath d='M20 8 L30 28 H24 L20 20 L16 28 H10 Z' fill='%23000000'/%3E%3Ctext x='45' y='24' font-family='Times New Roman' font-weight='bold' font-size='14' fill='%23000000'%3EArcteron Trust%3C/text%3E%3C/g%3E%3C/svg%3E");
            }

            /* Header part of card */
            .rcp-header {
                padding: 24px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                position: relative;
                z-index: 1;
            }
            .rcp-logo-wrap {
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .rcp-logo-wrap span {
                font-family: 'Cormorant Garamond', serif;
                font-size: 18px;
                font-weight: 700;
            }
            .rcp-header-label {
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                color: var(--text-muted, #9CA3AF);
            }

            .rcp-close-btn {
                background: none;
                border: none;
                font-size: 24px;
                color: var(--text-muted, #9CA3AF);
                cursor: pointer;
                padding: 0;
                line-height: 1;
                transition: color 0.2s ease;
            }
            .rcp-close-btn:hover {
                color: var(--text-primary, #F9FAFB);
            }

            .rcp-body {
                padding: 0 24px 24px;
                position: relative;
                z-index: 1;
            }

            /* Amount Section */
            .rcp-amount-section {
                text-align: center;
                margin-top: 8px;
                margin-bottom: 24px;
            }
            .rcp-amount {
                font-family: 'Cormorant Garamond', serif;
                font-size: 42px;
                font-weight: 700;
                margin-bottom: 8px;
                line-height: 1;
            }
            .rcp-amount.credit { color: #10B981; }
            .rcp-amount.debit { color: #EF4444; }
            
            .rcp-status {
                font-size: 14px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            .rcp-status.completed { color: #10B981; }
            .rcp-status.pending { color: #F59E0B; }
            .rcp-status.failed { color: #EF4444; }

            .rcp-datetime {
                font-size: 13px;
                color: var(--text-secondary, #9CA3AF);
                margin-top: 6px;
            }

            /* Dividers */
            .rcp-divider {
                width: 100%;
                height: 0;
                border-top: 1.5px dashed var(--border-color, #374151);
                margin: 20px 0;
                opacity: 0.6;
            }

            /* Info Rows */
            .rcp-info-list {
                display: flex;
                flex-direction: column;
                gap: 16px;
            }
            .rcp-row {
                display: flex;
                justify-content: space-between;
                align-items: flex-start;
                gap: 16px;
            }
            .rcp-label {
                font-size: 13px;
                color: var(--text-muted, #9CA3AF);
                flex: 0 0 auto;
                padding-top: 2px;
            }
            .rcp-value {
                font-size: 14px;
                font-weight: 600;
                color: var(--text-primary, #F9FAFB);
                text-align: right;
                word-break: break-word;
            }

            /* Footer tagline */
            .rcp-footer-tagline {
                font-size: 11px;
                color: var(--text-muted, #6B7280);
                text-align: center;
                line-height: 1.5;
                margin-top: 10px;
                padding: 0 10px;
            }

            /* Actions */
            .rcp-actions {
                display: flex;
                gap: 12px;
                width: 100%;
            }
            .rcp-btn {
                flex: 1;
                padding: 13px 24px; /* Consistent with .btn-primary */
                border-radius: 8px; /* Consistent with --radius-sm */
                font-family: inherit;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
                border: none;
                transition: opacity 0.2s ease, transform 0.1s ease; /* Consistent with .btn-primary */
            }
            .rcp-btn:hover {
                opacity: 0.85; /* Consistent with .btn-primary */
            }
            .rcp-btn:active {
                transform: scale(0.99); /* Consistent with .btn-primary */
            }
            .rcp-btn-secondary {
                background: transparent;
                color: var(--text-primary);
                border: 1px solid var(--border-color);
                font-weight: 500; /* Consistent with .btn-secondary */
            }
            [data-theme="light"] .rcp-btn-secondary {
                background: #FFFFFF;
                color: var(--text-primary);
            }
            .rcp-btn-secondary:hover {
                background: var(--bg-primary); /* Consistent with .btn-secondary */
                filter: none;
            }
            .rcp-btn-primary {
                background: var(--text-primary); /* Consistent with .btn-primary */
                color: var(--bg-primary); /* Consistent with .btn-primary */
            }

            /* Mobile tweaks */
            @media (max-width: 480px) {
                .rcp-modal {
                    position: fixed;
                    top: 20px;
                    bottom: 20px;
                    left: 20px;
                    right: 20px;
                    width: auto;
                    max-width: none;
                    margin: 0;
                    border-radius: 16px;
                    background: transparent;
                }
                .rcp-capture-area {
                    border-radius: 16px;
                }
                .rcp-actions {
                    padding: 0 20px 20px;
                    flex-direction: column;
                }
            }
        `;
        document.head.appendChild(style);
    }

    /**
     * Display the modal directly with passed data (Legacy/fallback)
     */
    function open(data) {
        if (!isInitialized) init();
        currentTransactionId = data.transactionId || data.id || null;
        currentReceiptData = data;

        const isCredit = data.isCredit || data.is_credit;
        const fmt = (n) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n || 0);

        let amt = Number(data.amount) || 0;
        const amountEl = document.getElementById('rcpAmount');
        amountEl.textContent = (isCredit ? '+' : '-') + fmt(amt);
        amountEl.className = 'rcp-amount ' + (isCredit ? 'credit' : 'debit');

        const statusEl = document.getElementById('rcpStatus');
        const st = (data.status || 'Completed').toLowerCase();
        statusEl.textContent = st.charAt(0).toUpperCase() + st.slice(1);
        statusEl.className = 'rcp-status ' + st;

        document.getElementById('rcpDateTime').textContent = `${data.date || ''} · ${data.time || ''}`;

        document.getElementById('rcpPartyLabel').textContent = isCredit ? 'Transfer From' : 'Transfer To';
        document.getElementById('rcpParty').textContent = data.party || data.recipient_name || 'External Sender';
        document.getElementById('rcpRef').textContent = data.reference || '—';
        document.getElementById('rcpBank').textContent = data.bank || data.recipient_bank || 'Arcteron Trust';
        document.getElementById('rcpDescription').textContent = data.description || '—';

        let typeStr = (data.type || data.transaction_type || 'Transfer');
        typeStr = typeStr.replace(/_/g, ' ');
        // Title Case
        typeStr = typeStr.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ');
        document.getElementById('rcpType').textContent = typeStr;

        // Logic matches PDF:
        // Receiving (Credit): full local account, masked sender account
        // Sending (Debit): masked local account, full recipient account
        let recAcctStr = data.recipientAccount || data.recipient_account;
        let myAcctStr = data.account || data.own_account_number;

        if (isCredit) {
            document.getElementById('rcpRecipientAcct').textContent = maskAccountNumber(recAcctStr);
            document.getElementById('rcpAccount').textContent = formatFullAccountNumber(myAcctStr);
        } else {
            document.getElementById('rcpRecipientAcct').textContent = formatFullAccountNumber(recAcctStr);
            document.getElementById('rcpAccount').textContent = maskAccountNumber(myAcctStr);
        }

        modalElement.classList.add('show');
    }

    /**
     * Unified Fetch: Takes an ID, fetches from new endpoint, formats, and calls open()
     */
    async function openById(txId) {
        if (!txId) return;
        const token = typeof Api !== 'undefined' ? Api.getToken() : localStorage.getItem('arcteronToken');
        const API_BASE = typeof Api !== 'undefined' && Api.API_BASE ? Api.API_BASE : 'https://arcteron-trust.onrender.com';

        try {
            const res = await fetch(`${API_BASE}/api/transactions/${txId}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!res.ok) throw new Error('Transaction not found');
            const tx = await res.json();

            // Format time correctly if TimeUtils is present
            let dateStr = "—";
            let timeStr = "—";
            let displayDate = tx.transaction_date || tx.created_at;
            if (typeof TimeUtils !== 'undefined') {
                dateStr = TimeUtils.formatDate(displayDate);
                timeStr = TimeUtils.formatTimeUTC(displayDate);
            } else {
                const d = new Date(displayDate);
                dateStr = d.toLocaleDateString();
                timeStr = d.toLocaleTimeString() + " UTC";
            }

            open({
                id: tx.id,
                transactionId: tx.id,
                amount: tx.amount,
                isCredit: tx.is_credit,
                status: tx.status,
                date: dateStr,
                time: timeStr,
                party: tx.is_credit ? (tx.sender_name || 'External Sender') : (tx.recipient_name || 'Unknown Recipient'),
                bank: tx.recipient_bank,
                reference: tx.reference,
                type: tx.transaction_type,
                recipientAccount: tx.recipient_account,
                account: tx.own_account_number,
                description: tx.description || '—'
            });

        } catch (err) {
            console.error('Failed to load transaction details', err);
            // Fallback: alert the user
            alert('Failed to load receipt details. Please try again.');
        }
    }

    function close() {
        if (modalElement) modalElement.classList.remove('show');
    }

    function downloadReceipt() {
        if (!currentTransactionId) return;
        const token = typeof Api !== 'undefined' ? Api.getToken() : localStorage.getItem('arcteronToken');
        const API_BASE = typeof Api !== 'undefined' && Api.API_BASE ? Api.API_BASE : 'https://arcteron-trust.onrender.com';
        const theme = document.documentElement.getAttribute('data-theme') || 'dark';

        const url = `${API_BASE}/api/transactions/${currentTransactionId}/receipt?theme=${theme}`;

        // Show loading state on button
        const btn = document.getElementById('rcpDlBtn'); // we didn't specify ID for PDF button, lets rely on class or just ignore

        fetch(url, { headers: { 'Authorization': `Bearer ${token}` } })
            .then(res => {
                if (!res.ok) throw new Error('Could not download receipt');
                return res.blob();
            })
            .then(blob => {
                const objUrl = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = objUrl;
                a.download = `Arcteron_Receipt_${currentTransactionId.substring(0, 8)}.pdf`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(objUrl);
            })
            .catch(err => {
                alert('Failed to download receipt: ' + err.message);
            });
    }

    async function shareAsImage() {
        // Ensure html2canvas is passed along globally
        if (typeof html2canvas === 'undefined') {
            alert('Image sharing is loading... please wait a second and try again.');
            return;
        }

        const captureElem = document.getElementById('receiptCaptureArea');
        const btn = document.getElementById('btnShareImg');
        const originalText = btn.innerHTML;
        btn.innerHTML = 'Generating...';

        try {
            // Wait slightly for fonts/rendering
            await new Promise(r => setTimeout(r, 100));

            const canvas = await html2canvas(captureElem, {
                scale: 2,
                useCORS: true,
                backgroundColor: null,
                logging: false,
                windowWidth: captureElem.scrollWidth,
                windowHeight: captureElem.scrollHeight
            });

            // Convert to blob
            canvas.toBlob(async (blob) => {
                const filename = `Arcteron_Receipt_${currentTransactionId ? currentTransactionId.substring(0, 8) : 'export'}.png`;

                // Try to use Web Share API
                if (navigator.canShare && navigator.canShare({ files: [new File([blob], filename, { type: 'image/png' })] })) {
                    try {
                        const file = new File([blob], filename, { type: 'image/png' });
                        await navigator.share({
                            files: [file],
                            title: 'Arcteron Trust Receipt',
                            text: 'Transaction Receipt from Arcteron Trust'
                        });
                    } catch (e) {
                        if (e.name !== 'AbortError') {
                            downloadBlob(blob, filename);
                        }
                    }
                } else {
                    downloadBlob(blob, filename);
                }
                btn.innerHTML = originalText;
            }, 'image/png');

        } catch (err) {
            console.error('Image capture failed', err);
            alert('Failed to generate image. Please try downloading PDF instead.');
            btn.innerHTML = originalText;
        }
    }

    function downloadBlob(blob, filename) {
        const objUrl = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = objUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(objUrl);
    }

    // Public API
    return {
        init,
        open,
        openById,
        close,
        downloadReceipt,
        shareAsImage,
        maskAccountNumber,
        formatAccountNumber: formatFullAccountNumber
    };
})();

// Expose
window.ReceiptModal = ReceiptModal;
