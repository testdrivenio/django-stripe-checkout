import stripe
from django.conf import settings
from django.http.response import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import TemplateView


class HomePageView(TemplateView):
    template_name = 'home.html'


@csrf_exempt
def stripe_config(request):
    if request.method == 'GET':
        stripe_config = {'publicKey': settings.STRIPE_PUBLISHABLE_KEY}
        return JsonResponse(stripe_config, safe=False)


@csrf_exempt
def create_checkout_session(request):
    if request.method == 'GET':
        domain_url = 'http://localhost:8000/'
        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            # Create new Checkout Session for the order
            # Other optional params include:
            # [billing_address_collection] - to display billing address details on the page
            # [customer] - if you have an existing Stripe Customer ID
            # [payment_intent_data] - lets capture the payment later
            # [customer_email] - lets you prefill the email input in the form
            # For full details see https:#stripe.com/docs/api/checkout/sessions/create

            # ?session_id={CHECKOUT_SESSION_ID} means the redirect will have the session ID set as a query param

            # If we want to identify the user when using webhooks we can pass client_reference_id  to checkout
            # session constructor. We will then be able to fetch it and make changes to our Django models.
            #
            # If we offer a SaaS service it would also be good to allow only authenticated users to purchase
            # anything on our site.

            checkout_session = stripe.checkout.Session.create(
                # client_reference_id=request.user.id if request.user.is_authenticated else None,
                success_url=domain_url + 'success?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=domain_url + 'cancelled/',
                payment_method_types=['card'],
                mode='payment',
                line_items=[
                    {
                        'name': 'T-shirt',
                        'quantity': 1,
                        'currency': 'usd',
                        'amount': '2000',
                    }
                ]
            )
            return JsonResponse({'sessionId': checkout_session['id']})
        except Exception as e:
            return JsonResponse({'error': str(e)})


@csrf_exempt
def stripe_webhook(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    endpoint_secret = settings.STRIPE_ENDPOINT_SECRET
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None

    # Stripe CLI setup + login
    # The easiest way to test our webhook is to download Stripe CLI (https://stripe.com/docs/stripe-cli)
    # After downloading it we need to login by running 'stripe login' in Terminal, this command will generate
    # a pairing code for us an open our web browser.
    #
    # ---------------------------------------------------------------
    # Your pairing code is: word1-word2-word3-word4
    # This pairing code verifies your authentication with Stripe.
    # Press Enter to open the browser (^C to quit)
    # ---------------------------------------------------------------
    #
    # By pressing enter CLI opens our browser and asks us if we want to allow Stripe CLI to access our account
    # information. We can allow it by clicking 'Allow access' button and confirming the action with our password.
    #
    # If everything goes well Stripe CLI will display the following message:
    #
    # ---------------------------------------------------------------
    # > Done! The Stripe CLI is configured for {ACCOUNT_NAME} with account id acct_{ACCOUNT_ID}
    # Please note: this key will expire after 90 days, at which point you'll need to re-authenticate.
    # ---------------------------------------------------------------
    #
    # Webhook setup
    # Once we successfully logged in we can start listening to Stripe events and forward them to our webhook using
    # the following command:
    #
    # stripe listen --forward-to localhost:8000/webhook/
    #
    # This will generate a webhook signing secret that we should save in our settings.py. After that we will
    # need to pass it when constructing a Webhook event.
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return HttpResponse(status=400)

    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']

        # This method will be called when user successfully purchases something.
        handle_checkout_session(session)

    return HttpResponse(status=200)


def handle_checkout_session(session):
    # client_reference_id = user's id
    client_reference_id = session.get("client_reference_id")
    payment_intent = session.get("payment_intent")

    if client_reference_id is None:
        # Customer wasn't logged in when purchasing
        return

    # Customer was logged in we can now fetch the Django user and make changes to our models
    try:
        user = User.objects.get(id=client_reference_id)
        print(user.username, "just purchased something.")

        # TODO: make changes to our models.

    except User.DoesNotExist:
        pass


class SuccessView(TemplateView):
    template_name = 'success.html'


class CancelledView(TemplateView):
    template_name = 'cancelled.html'


@csrf_exempt
def stripe_webhook(request):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    endpoint_secret = 'whsec_TVXgZgjYDrryuUocfcMhUlhoj9p0C0sc'
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return HttpResponse(status=400)

    # Handle the checkout.session.completed event
    print(event['type'])
    if event['type'] == 'checkout.session.completed':
        print("Payment was successful.")
        # TODO: run some custom code here

    return HttpResponse(status=200)
