package com.leeyom.scaffold.dto.req;

import lombok.Data;

@Data
public class User {

    private String id;

    private String buyeruid;

    /**
     * Year of birth as a 4-digit integer.
     * for example : 1990、2020
     */
    private String yob;

    private String gender;

    private UserExt ext;
}
