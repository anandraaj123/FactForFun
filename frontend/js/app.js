/**
 * Fact₹1 Main Client Application
 * Pure Minimalist Flow: ( Fact ₹1 ) -> Pay ₹1 -> Reveal Fact -> ( Fact ₹1 )
 */

(function () {
  'use strict';

  const STATE = {
    sessionId: null,
    currentFact: null,
    isProcessing: false,
    activeOrder: null,
  };

  const DOM = {
    initialHeroSection: document.getElementById('initialHeroSection'),
    revealedFactCard: document.getElementById('revealedFactCard'),
    btnMainFactPay: document.getElementById('btnMainFactPay'),
    btnBuyAnotherFact: document.getElementById('btnBuyAnotherFact'),
    
    revealedTitle: document.getElementById('revealedTitle'),
    revealedStatement: document.getElementById('revealedStatement'),
    revealedExplanation: document.getElementById('revealedExplanation'),

    // Modals & Toast
    simModal: document.getElementById('simPaymentModal'),
    btnSimPaySuccess: document.getElementById('btnSimPaySuccess'),
    btnSimCancel: document.getElementById('btnSimCancel'),
    toast: document.getElementById('toast'),
    toastMessage: document.getElementById('toastMessage')
  };

  function initSession() {
    let sess = localStorage.getItem('fact1_session_id');
    if (!sess) {
      sess = 'sess_' + Math.random().toString(36).substring(2, 15) + Date.now().toString(36);
      localStorage.setItem('fact1_session_id', sess);
    }
    STATE.sessionId = sess;
  }

  function init() {
    initSession();
    setupEventListeners();
  }

  async function handleFactPayClick() {
    if (STATE.isProcessing) return;
    STATE.isProcessing = true;

    if (DOM.btnMainFactPay) {
      DOM.btnMainFactPay.innerHTML = '<span class="pill-text">Opening Payment...</span>';
    }
    if (DOM.btnBuyAnotherFact) {
      DOM.btnBuyAnotherFact.innerHTML = '<span class="pill-text">Processing ₹1...</span>';
    }

    try {
      // Create ₹1 order on backend (auto-selects a random unread fact)
      const res = await fetch('/api/payments/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: STATE.sessionId
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Could not initiate payment');
      }

      const orderData = await res.json();
      STATE.activeOrder = orderData;

      if (orderData.gateway_name === 'cashfree' && window.Cashfree) {
        launchCashfreeCheckout(orderData);
      } else if (orderData.gateway_name === 'razorpay' && window.Razorpay) {
        launchRazorpayCheckout(orderData);
      } else {
        launchSimulatorCheckout(orderData);
      }
    } catch (err) {
      showToast(err.message || 'Payment initiation failed');
      resetButtons();
    }
  }

  function launchCashfreeCheckout(orderData) {
    try {
      const cashfree = window.Cashfree({
        mode: orderData.cashfree_env || "sandbox"
      });
      const checkoutOptions = {
        paymentSessionId: orderData.payment_session_id,
        redirectTarget: "_modal"
      };
      cashfree.checkout(checkoutOptions).then((result) => {
        if (result.error) {
          showToast(result.error.message || 'Payment cancelled');
          resetButtons();
        }
        if (result.paymentDetails) {
          verifyPaymentOnBackend({
            order_id: orderData.order_id,
            gateway_order_id: orderData.gateway_order_id,
            gateway_payment_id: "cf_success",
            session_id: STATE.sessionId
          });
        }
      });
    } catch (err) {
      showToast('Cashfree error: ' + err.message);
      resetButtons();
    }
  }

  function launchRazorpayCheckout(orderData) {
    const options = {
      key: orderData.gateway_key_id,
      amount: orderData.amount,
      currency: orderData.currency,
      name: 'Fact₹1',
      description: 'Unlock 1 Fact',
      order_id: orderData.gateway_order_id,
      handler: async function (response) {
        await verifyPaymentOnBackend({
          order_id: orderData.order_id,
          gateway_order_id: response.razorpay_order_id,
          gateway_payment_id: response.razorpay_payment_id,
          gateway_signature: response.razorpay_signature,
          session_id: STATE.sessionId
        });
      },
      theme: { color: '#000000' },
      modal: {
        ondismiss: function () {
          resetButtons();
          showToast('Payment cancelled.');
        }
      }
    };

    const rzp = new window.Razorpay(options);
    rzp.on('payment.failed', function () {
      resetButtons();
      showToast('Payment failed. Please retry.');
    });
    rzp.open();
  }

  function launchSimulatorCheckout() {
    DOM.simModal.style.display = 'flex';
  }

  async function handleSimulatorPaymentSuccess() {
    DOM.simModal.style.display = 'none';
    if (!STATE.activeOrder) return;

    showToast('Verifying payment...');

    const simulatedPaymentId = 'sim_pay_' + Math.random().toString(36).substring(2, 12);
    await verifyPaymentOnBackend({
      order_id: STATE.activeOrder.order_id,
      gateway_order_id: STATE.activeOrder.gateway_order_id,
      gateway_payment_id: simulatedPaymentId,
      gateway_signature: 'simulated_valid_signature',
      session_id: STATE.sessionId
    });
  }

  async function verifyPaymentOnBackend(payload) {
    try {
      const res = await fetch('/api/payments/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Payment verification failed');
      }

      const verifyData = await res.json();
      if (verifyData.success && verifyData.fact) {
        displayRevealedFact(verifyData.fact);
      } else {
        throw new Error('Could not retrieve fact');
      }
    } catch (err) {
      showToast(err.message);
    } finally {
      resetButtons();
    }
  }

  function displayRevealedFact(fact) {
    STATE.currentFact = fact;

    DOM.initialHeroSection.style.display = 'none';
    DOM.revealedFactCard.style.display = 'block';

    DOM.revealedTitle.textContent = fact.title || 'DID YOU KNOW?';
    DOM.revealedStatement.textContent = fact.fact_text || fact.fact;
    DOM.revealedExplanation.textContent = fact.explanation || '';

    showToast('✨ Fact Unlocked for ₹1');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function resetButtons() {
    STATE.isProcessing = false;
    const buttonHtml = `
      <span class="pill-bracket">(</span>
      <span class="pill-text">Fact ₹1</span>
      <span class="pill-bracket">)</span>
    `;
    if (DOM.btnMainFactPay) DOM.btnMainFactPay.innerHTML = buttonHtml;
    if (DOM.btnBuyAnotherFact) DOM.btnBuyAnotherFact.innerHTML = buttonHtml;
  }

  function showToast(message) {
    DOM.toastMessage.textContent = message;
    DOM.toast.classList.add('show');
    setTimeout(() => {
      DOM.toast.classList.remove('show');
    }, 2800);
  }

  function setupEventListeners() {
    DOM.btnMainFactPay?.addEventListener('click', handleFactPayClick);
    DOM.btnBuyAnotherFact?.addEventListener('click', handleFactPayClick);

    DOM.btnSimPaySuccess?.addEventListener('click', handleSimulatorPaymentSuccess);
    DOM.btnSimCancel?.addEventListener('click', () => {
      DOM.simModal.style.display = 'none';
      resetButtons();
    });

    document.querySelectorAll('.modal-close, .modal-overlay').forEach(el => {
      el.addEventListener('click', (e) => {
        if (e.target === el) {
          DOM.simModal.style.display = 'none';
          resetButtons();
        }
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
