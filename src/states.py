class RegistrationState:
    AWAITING_FIRST_NAME = "awaiting_first_name"
    AWAITING_CUSTOMER_BIRTHDATE = "awaiting_customer_birthdate"
    AWAITING_CHILD_NAME = "awaiting_child_name"
    AWAITING_CHILD_GENDER = "awaiting_child_gender"
    AWAITING_CHILD_BIRTHDATE = "awaiting_child_birthdate"
    AWAITING_MORE_CHILDREN = "awaiting_more_children"
    REGISTERED = "registered"

    SURVEY_STATES = {
        AWAITING_FIRST_NAME,
        AWAITING_CUSTOMER_BIRTHDATE,
        AWAITING_CHILD_NAME,
        AWAITING_CHILD_GENDER,
        AWAITING_CHILD_BIRTHDATE,
        AWAITING_MORE_CHILDREN,
    }
