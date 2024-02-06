from datetime import timedelta
import logging

import voluptuous as vol

import requests

import json
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import ATTR_ATTRIBUTION, CONF_API_KEY, CONF_NAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity import Entity
from homeassistant.components.text import TextEntity
from homeassistant.util import Throttle

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Information provided by BPost"
ATTR_TRACKINGS = "trackings"

CONF_NEW_JSON = "new_json_array"

DEFAULT_NAME = "bpost"
UPDATE_TOPIC = f"{DOMAIN}_update"

ICON = "mdi:package-variant-closed"

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=30)

SERVICE_ADD_TRACKING = "add_tracking"
# SERVICE_REMOVE_TRACKING = "remove_tracking"

ADD_TRACKING_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NEW_JSON): cv.string,
    }
)
#
# REMOVE_TRACKING_SERVICE_SCHEMA = vol.Schema(
#     {vol.Required(CONF_CARRIER_CODE): cv.string, vol.Required(CONF_TRACKING_NUMBER): cv.string}
# )

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the BPost sensor platform."""
    apikey = config[CONF_API_KEY]
    name = config[CONF_NAME]

    session = async_get_clientsession(hass)

    list_instance = TrackItemListSensor(name)

    async_add_entities([list_instance], True)

    instance = BPostSensor(name, list_instance)

    async_add_entities([instance], True)


    async def handle_add_tracking(call):
        """Call when a user adds a new BPost tracking from Home Assistant."""
        new_json = call.data.get(CONF_NEW_JSON)

        list_instance.set_value(new_json)
        async_dispatcher_send(hass, UPDATE_TOPIC)

    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_TRACKING,
        handle_add_tracking,
        schema=ADD_TRACKING_SERVICE_SCHEMA,
    )

    # async def handle_remove_tracking(call):
    #     """Call when a user removes an TrackTry tracking from Home Assistant."""
    #     carrier_code = call.data[CONF_CARRIER_CODE]
    #     tracking_number = call.data[CONF_TRACKING_NUMBER]
    #
    #     #await bpost.remove_package_tracking(carrier_code, tracking_number)
    #     async_dispatcher_send(hass, UPDATE_TOPIC)
    #
    # hass.services.async_register(
    #     DOMAIN,
    #     SERVICE_REMOVE_TRACKING,
    #     handle_remove_tracking,
    #     schema=REMOVE_TRACKING_SERVICE_SCHEMA,
    # )


class BPostSensor(Entity):
    """Representation of a BPost sensor."""

    def __init__(self, name, list_sensor):
        """Initialize the sensor."""
        self._attributes = {'hidden': False,"debug":"test"}
        self._name = name
        self._state = None
        self._list_sensor = list_sensor

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return "packages"

    @property
    def extra_state_attributes(self):
        """Return attributes for the sensor."""
        return self._attributes

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return ICON

    def get_codes(self):
        state = self.hass.states.get("input_text.tracking_codes")
        return state


    async def async_added_to_hass(self):
        """Register callbacks."""
        self.async_on_remove(
            self.hass.helpers.dispatcher.async_dispatcher_connect(
                UPDATE_TOPIC, self._force_update
            )
        )

    async def _force_update(self):
        """Force update of data."""
        await self.async_update(no_throttle=True)
        self.async_write_ha_state()

    trackings = []

    def fetch_tracking_object(self, code, postalCode):

        response = (requests.get("https://track.bpost.cloud/track/items?v=3&itemIdentifier=" + str(code) + "&postalCode=" + str(postalCode)))
        #return json.loads(
        #    """{"items":[{"key":{"id":1134233104,"created":1706734895000,"primaryKey":"1134233104-1706734895000","tmmId":"22640402489","tmmCreated":"1706731294737","tmmPrimaryKey":"22640402489-1706731294737","version":15},"searchCode":"323212505100043382188030","itemCode":"323212505100043382188030","senderBarcode":"BPOST","customerReference":"UVZDYTDRP","customerAccountId":"125051","trackingCategory":"FULLY TRACKED","retourOrBackToSender":false,"isfinalMileCarrier":false,"countryOfDepurture":"BE","signatureViewType":"NONE","senderCommercialName":"Amazon","instancesOfPugoPointChange":[],"shipmentType":"National","showStopsandProgressBar":false,"candidateForFDR":false,"parcelImageReferences":[],"sustainability":{"info":{"positive":{"EN":{"title":"Together, we can reduce CO<sub>2</sub> emissions by 90%!","desc":"Have your next parcels delivered directly to your favorite Pick-up point. It's good for the environment and you don't necessarily have to wait at home for the postman."},"FR":{"title":"Envie de nous aider à réduire nos émissions de CO<sub>2</sub> de 90 % ?","desc":"Faites livrer vos colis directement dans votre Point d’enlèvement préféré. Passez les récupérer quand vous le souhaitez et c'est aussi bon pour l'environnement."},"NL":{"title":"Klaar om samen tot 90% CO<sub>2</sub> te besparen?","desc":"Ja dat kan. Laat je volgende pakjes rechtstreeks in jouw favoriete Afhaalpunt leveren. Zo hoef je niet thuis te wachten en haal je ze op wanneer het jou uitkomt."}}}},"greenDeliveries":{"postalCodeFound":true,"postalCodePercentage":10.04,"shipmentDeliveredGreenWay":false,"romaRoundMainTransportType":"Car"},"roundName":"Res-104","events":[{"date":"2024-02-01","time":"08:43","key":{"EN":{"description":"Item delivered"},"FR":{"description":"Envoi distribué"},"NL":{"description":"Zending geleverd"}},"irregularity":false},{"date":"2024-02-01","time":"07:52","key":{"EN":{"description":"Item in distribution phase"},"FR":{"description":"Envoi en route pour distribution"},"NL":{"description":"Zending onderweg voor levering"}},"irregularity":false},{"date":"2024-02-01","time":"07:45","key":{"EN":{"1":"Your {{productCategoryName}} is being prepared by the postman.","2":"We expect to deliver it","3":"<span class='step-strong'> {{expectedDeliveryDate}}</span>","4":"to the address mentioned below.","5":"As soon as the postman starts his round, we will inform you on a more exact delivery time.","6":"<br><br>Due to the size or weight of your parcel, our partner Dynalogic delivers your parcel.","description":"Shipment being prepared by the postman"},"FR":{"1":"Votre {{productCategoryName}} est en cours de préparation par le facteur.","2":"Nous prévoyons de livrer votre {{productCategoryName}}","3":"<span class='step-strong'>{{expectedDeliveryDate}}</span>","4":"à l'adresse mentionnée ci-dessous.","5":"Dès que le facteur commencera sa tournée, nous vous informerons d’un délai de livraison plus précis.","6":"<br><br>Notre partenaire Dynalogic se charge de la livraison de votre colis, en raison de sa taille ou son poids.","description":"L'envoi est en cours de préparation par le facteur"},"NL":{"1":"Je {{productCategoryName}} wordt door de postbode klaargemaakt.","2":"We verwachten het af te leveren","3":"<span class='step-strong'> {{expectedDeliveryDate}}</span>","4":"op het hieronder vermelde adres.","5":"Zodra de postbode met zijn ronde begint, zullen we je op de hoogte brengen van een preciezer levertijdstip.","6":"<br><br>Door de omvang of gewicht van je pakje, levert onze partner Dynalogic je pakje.","description":"Zending wordt voorbereid door de postbode"}},"irregularity":false},{"date":"2024-02-01","time":"01:11","key":{"EN":{"description":"Your item has been sorted"},"FR":{"description":"L'envoi a été trié"},"NL":{"description":"De zending werd gesorteerd"}},"irregularity":false},{"date":"2024-01-31","time":"21:01","key":{"EN":{"description":"Confirmation of preparation of the shipment received"},"FR":{"description":"Informations relatives à l'envoi reçues de la part de l'expéditeur"},"NL":{"description":"Informatie over de zending ontvangen van de afzender"}},"irregularity":false}],"weightInGrams":780,"dimensionsInCm":"23.5cm x 16cm x 31cm","showCallCenterCode":true,"orderDate":{"day":"2024-01-31","time":"21:01"},"actualDeliveryTime":{"day":"2024-02-01","time":"08:43"},"processOverview":{"alert":false,"activeStepTextKey":"DELIVERED","textKey":{"EN":{"1":"Your {{productCategoryName}} was delivered","2":"<span class='step-strong'> {{actualDeliveryDate}}</span>","3":"<span class='step-strong'> at {{actualDeliveryTime}}</span>","4":".","5":"bpost delivered your {{productCategoryName}} in {{totalInNetworkHours}} hours and {{totalInNetworkMinutes}} min."},"FR":{"1":"Votre {{productCategoryName}} a été livré","2":"<span class='step-strong'> {{actualDeliveryDate}}</span>","3":"<span class='step-strong'> à {{actualDeliveryTime}}</span>","4":". ","5":"bpost a livré votre {{productCategoryName}} en {{totalInNetworkHours}} heures et {{totalInNetworkMinutes}} min. "},"NL":{"1":"Je {{productCategoryName}} werd","2":"<span class='step-strong'> {{actualDeliveryDate}}</span>","3":"<span class='step-strong'> om {{actualDeliveryTime}}</span>","4":" afgeleverd. ","5":"bpost leverde je {{productCategoryName}} in {{totalInNetworkHours}} uur en {{totalInNetworkMinutes}} min."}},"processSteps":[{"name":"prepare","status":"completed","knownProcessStep":"IN_PREPARATION","label":{"main":"inPreparation","detail":"parcel"}},{"name":"processing","status":"completed","knownProcessStep":"PROCESSING","label":{"main":"processing","detail":"byBpost"}},{"name":"out_for_delivery_byCar","status":"completed","knownProcessStep":"ON_THE_WAY_TO_YOU","label":{"main":"onTheWay","detail":"toYou"}},{"name":"delivered","status":"active","knownProcessStep":"DELIVERED_AT_HOME","label":{"main":{"EN":"Delivered","FR":"Livré","NL":"Afgeleverd"},"detail":{"EN":"at home","FR":"chez vous","NL":"aan huis"}}}]},"product":"2000000153582","productName":"bpack 24h pro","productCategory":"parcel","sender":{"name":"P A BRUSSELS X   AMAZON RETURNS","municipality":"Bruxelles X","postcode":"1099","countryCode":"BE","pdpId":"9318565","street":"CHAUSSÉE DE VILVORDE 233","streetName":"CHAUSSÉE DE VILVORDE","streetNumber":"233"},"receiver":{"name":"MATTI BIJNENS","municipality":"OUD-TURNHOUT","postcode":"2360","countryCode":"BE","pdpId":"1779609","street":"SCHUURHOVENBERG 35","streetName":"SCHUURHOVENBERG","streetNumber":"35"},"services":["2000000205199","2000000211634"],"requestedDeliveryMethod":"HOME","contactForMoreInformation":"SENDER","customs":{},"cost":null,"latestAvailableTime":{"day":"2024-02-16"},"inNetworkDate":"2024-02-01","eligibilities":{"eligibileForRerouting":false,"eligibileForPreferedAvisage":false,"eligibileForNeighbourDelivery":true,"eligibileForSafeplaceDelivery":true},"requestedPreferences":{"language":"NL","rerouting":{"address":{}},"reroutingStatus":{"active":false},"preferredAvisage":{"address":{"city":"TURNHOUT","street":"PARKLAAN","postalCode":"2300","streetNumber":"80-82"},"unitName":"CARREFOUR TURNHOUT","avisageAcCode":"12193"},"activePreferenceKey":"6119358394-283034761","fallbackDeliveryType":"SAFEPLACE","matchedSecurityLevel":{"matchedReason":"NAME","securityLevel":"LOW"},"applicableForDirection":"TO_ADDRESSEE","fallbackDeliveryStatus":{"active":true},"preferredAvisageStatus":{"active":true}},"actualDeliveryInformation":{"description":"undefined","actualDeliveryTime":{"day":"2024-02-01","time":"08:43"}},"activeForDeliveryPreferences":false,"faqs":["ALLOW_NEIGHBOUR_DELIVERY","PARCEL","ALLOW_SAFEPLACE_DELIVERY","ALLOW_REDELIVERY","SATURDAY_DELIVERY","ALLOW_BPACK247","ALLOW_GROUPING_ON_DELIVERY","DELIVERED_AT_HOME","AT_HOME","IN_NETWORK","CUSTOMS_PAYMENT_NOT_REQUIRED"],"faqIds":[1709,749,734],"webformUrl":{"en":"https://www.bpost.be/en/forms/customs/step1?barcode=323212505100043382188030","fr":"https://www.bpost.be/fr/formulaires/douane/step1?barcode=323212505100043382188030","nl":"https://www.bpost.be/nl/formulieren/douane/step1?barcode=323212505100043382188030"},"totalInNetworkTime":{"hours":7,"minutes":32},"matchSecurityLevel":false,"isItemReroutedforPickupPoint":false,"isItemReroutedforProcessing":false,"showDeliveryPreferences":false,"lockerDetailsDropOff":{},"isGDPRCompliant":true,"isEligibleForSFM":false,"preferenceInfo":{"preferenceTextKey":"20-sp-success","hidePreferenceChangeButton":true},"isAdvisedItem":false,"reasonCode":"distribution.normal-in_person","hasSecureDeliveryCode":false,"activeStep":{"name":"delivered","status":"active","knownProcessStep":"DELIVERED_AT_HOME","label":{"main":{"EN":"Delivered","FR":"Livré","NL":"Afgeleverd"},"detail":{"EN":"at home","FR":"chez vous","NL":"aan huis"}}},"isChatbot":true,"deliveryPreferenceType":"SAFEPLACE","isDeliveryPreferenceActive":true,"deliveryPreferenceRejectCode":null,"dutyAmountDetails":[]}],"listOfParcelItemsByEmailIds":[]}""")
        response_json = response.json()
        if 'error' in response_json and response_json["error"] == "NO_DATA_FOUND":
            return response_json
        return response_json["items"][0]
    def get_trackings(self):
        
        to_track = json.loads(self._list_sensor.state)
        self.trackings = []
        for obj in to_track:
            self.trackings.append(self.fetch_tracking_object(obj["code"], obj["postalCode"]))


    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def async_update(self, **kwargs):
        """Get the latest data from the BPost API."""
        result = await self.hass.async_add_executor_job(self.get_trackings)
        status_to_ignore = {"delivered"}
        status_counts = {}
        trackings = []
        not_delivered_count = 0

        for track in self.trackings:
            if 'error' in track and track["error"] == "NO_DATA_FOUND":
                trackings.append({"not found"})
                continue
            status = track['activeStep']['name']
            name = track['sender']['name'],
            last_update_time = 'Never Updated'
            expected_delivery_time = {}
            if "expectedDeliveryTimeRange" in track:
                expected_delivery_time = track["expectedDeliveryTimeRange"]

            trackings.append(
                {
                    "name": track['sender']['name'],
                    "tracking_number": track['itemCode'],
                    "last_update_time": "Never",
                    "expected_delivery_time": expected_delivery_time,
                    "status": track['activeStep']['name']
                }
            )

            if status not in status_to_ignore:
                not_delivered_count += 1
            else:
                _LOGGER.debug("Ignoring %s as it has status: %s", name, status)

        self._attributes = {
            "matti":"bijnens",
            ATTR_ATTRIBUTION: ATTRIBUTION,
            **status_counts,
            ATTR_TRACKINGS: trackings,
            'hidden': False
        }

        self._state = len(self.trackings)
class TrackItemListSensor(TextEntity):
    """Representation of a BPost sensor."""

    def __init__(self, name):
        """Initialize the sensor."""
        self._name = name
        self._native_max = 513
        self._native_value = '[{"code":"323212505100043382188030", "postalCode":"2360 "}]'
        self._state = '[{"code":"323212505100043382188030", "postalCode":"2360 "}]'

    @property
    def native_max(self):
        return 500

    @property
    def native_value(self):
        return self._state

    def set_value(self, value):
        self._state = value
        return value

    async def async_set_value(self, value: str):
        self._state = value
        return value
    @property
    def name(self):
        """Return the name of the sensor."""
        return "Codes to track"

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return "packages"

    @property
    def extra_state_attributes(self):
        """Return attributes for the sensor."""
        return {
            'hidden': False,
            "example":'[{"code":"323212505100043382188030", "postalCode":"2360 "}]'
        }

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return ICON
