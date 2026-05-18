class RegistrationState:
    AWAITING_FIRST_NAME = "awaiting_first_name"
    AWAITING_LAST_NAME = "awaiting_last_name"
    AWAITING_CUSTOMER_BIRTHDATE = "awaiting_customer_birthdate"
    AWAITING_CHILD_NAME = "awaiting_child_name"
    AWAITING_CHILD_GENDER = "awaiting_child_gender"
    AWAITING_CHILD_BIRTHDATE = "awaiting_child_birthdate"
    AWAITING_MORE_CHILDREN = "awaiting_more_children"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    AWAITING_CONTACT = "awaiting_contact"
    REGISTERED = "registered"

    SURVEY_STATES = {
        AWAITING_FIRST_NAME,
        AWAITING_LAST_NAME,
        AWAITING_CUSTOMER_BIRTHDATE,
        AWAITING_CHILD_NAME,
        AWAITING_CHILD_GENDER,
        AWAITING_CHILD_BIRTHDATE,
        AWAITING_MORE_CHILDREN,
        AWAITING_CONFIRMATION,
        AWAITING_CONTACT,
    }


class ProfileState:
    EDITING_CUSTOMER_FIELD = "editing_customer_field"
    EDITING_CHILD_FIELD = "editing_child_field"
    ADDING_CHILD_NAME = "adding_child_name"
    ADDING_CHILD_GENDER = "adding_child_gender"
    ADDING_CHILD_BIRTHDATE = "adding_child_birthdate"
    CONFIRMING_DELETE_CHILD = "confirming_delete_child"


class StaffState:
    AWAITING_CUSTOMER_ID = "awaiting_customer_id"
    AWAITING_DISCOUNT_VALUE = "awaiting_discount_value"
    AWAITING_BROADCAST_MSG = "awaiting_broadcast_msg"
    AWAITING_BROADCAST_RECIPIENTS = "awaiting_broadcast_recipients"
    AWAITING_BROADCAST_TIME = "awaiting_broadcast_time"
    AWAITING_SELLER_CONFIRM = "awaiting_seller_confirm"
    AWAITING_BROADCAST_COUPON_CHOICE = "awaiting_broadcast_coupon_choice"
    AWAITING_COUPON_VALUE = "awaiting_coupon_value"
    AWAITING_COUPON_DAYS = "awaiting_coupon_days"
    AWAITING_COUPON_PCT = "awaiting_coupon_pct"
