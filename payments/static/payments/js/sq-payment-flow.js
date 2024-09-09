async function SquarePaymentFlow() {

  // Create card payment object and attach to page
  CardPay(document.getElementById('card-container'), document.getElementById('card-button'));

  // Create Apple pay instance
  ApplePay(document.getElementById('apple-pay-button'));

  // Create Google pay instance
  GooglePay(document.getElementById('google-pay-button'));

  // Create ACH payment
  ACHPay(document.getElementById('ach-button'));

  // Create Cash App payment
  CashAppPay(document.getElementById('cash-app-pay'));
}

window.payments = Square.payments(window.applicationId, window.locationId);

window.paymentFlowMessageEl = document.getElementById('payment-flow-message');

window.showSuccess = function(message) {
  window.paymentFlowMessageEl.classList.add('success');
  window.paymentFlowMessageEl.classList.remove('error');
  window.paymentFlowMessageEl.innerText = message;
}

window.showError = function(message) {
  window.paymentFlowMessageEl.classList.add('error');
  window.paymentFlowMessageEl.classList.remove('success');
  window.paymentFlowMessageEl.innerText = message;
}

window.createPayment = async function(token) {
  const dataJsonString = JSON.stringify({
    token,
    idempotencyKey: window.idempotencyKey
  });


  try {
    const response = await fetch('process-payment/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: dataJsonString
    });

    const res = await response.json();
    
    const data = res.square_res;

    if (data.errors && data.errors.length > 0) {
      if (data.errors[0].detail) {
        window.showError(data.errors[0].detail);
      } else {
        window.showError('Payment Failed.');
      }
    } else {
      window.showSuccess('Payment Successful!');
      const paymentSuccessPage = res.payment_success_page;
      window.location = new URL(paymentSuccessPage, window.location.origin);
    }
  } catch (error) {
    console.error('Error:', error);
  }
}



SquarePaymentFlow();
