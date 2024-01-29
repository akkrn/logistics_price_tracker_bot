from enum import Enum
import jwt
import datetime


class WildberriesTokenScope(Enum):
    CONTENT = 1
    ANALYTICS = 2
    PRICES_DISCOUNTS = 3
    MARKETPLACE = 4
    STATISTICS = 5
    PROMOTION = 6
    FEEDBACKS_QUESTIONS = 7
    RECOMMENDATIONS = 8
    READONLY = 30


class WildberriesOldTokenTypeException(Exception):
    pass


class WildberriesToken:
    def __init__(self, token: str):
        self.__token = token
        self.__data = jwt.decode(token, options={"verify_signature": False})
        if 'acsessID' in self.__data:
            raise WildberriesOldTokenTypeException('Old token type')
        self.id = self.__data['id']
        self.expires_at = datetime.datetime.fromtimestamp(self.__data['exp'])
        self.supplier_id = self.__data['sid']
        self.issued_by = self.__data['iid']
        self.user_id = self.__data['uid']
        self.__init_scope()

    def __init_scope(self):
        self.scopes = []
        s = self.__data['s']
        for i in range(30):
            if s & 1:
                self.scopes.append(WildberriesTokenScope(i))
            s = s >> 1

    def get_time_to_expire(self):
        return self.expires_at - datetime.datetime.now()

    def is_expired(self):
        return self.expires_at < datetime.datetime.now()

    def has_scope(self, scope: WildberriesTokenScope):
        return scope in self.scopes

    def is_readonly(self):
        return self.has_scope(WildberriesTokenScope.READONLY)
