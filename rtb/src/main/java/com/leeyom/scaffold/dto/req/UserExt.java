package com.leeyom.scaffold.dto.req;

import lombok.Data;

@Data
public class UserExt {

    /**
     * '0' = all PII scrubbed
     * '1' = user has given consent
     */
    private Integer consent;
}
