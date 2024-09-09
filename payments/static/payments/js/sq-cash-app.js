async function CashAppPay(buttonEl) {
    const paymentRequest = window.payments.paymentRequest(
      // Use global method from sq-payment-flow.js
      window.getPaymentRequest()
    );
  
    let cashAppPay;
    try {
      cashAppPay = await window.payments.cashAppPay(paymentRequest, {
        redirectURL: window.location.href,
        referenceId: 'my-website-00000001',
      });
    } catch (e) {
      console.error(e)
      return;
    }
    const buttonOptions = {
        shape: 'semiround',
        width: 'full',
      };
  
    await cashAppPay.attach(buttonEl, buttonOptions);
    return cashAppPay;
  
  }
  
  cashAppPay.addEventListener('ontokenization', function (event) {
    const { tokenResult, error } = event.detail;
    if (error) {
      // developer handles error
    }
    else if (tokenResult.status === 'OK') {
      // developer passes token to backend for use with CreatePayment
    }
  });