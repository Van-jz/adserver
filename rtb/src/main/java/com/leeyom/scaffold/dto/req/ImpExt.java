package com.leeyom.scaffold.dto.req;

import lombok.Data;

import javax.validation.constraints.NotNull;

@Data
public class ImpExt {

    private Skadn skadn;

    private Integer deeplink;

    private Integer skpv;

    private Integer vxec;

    /**
     * cta
     * 1-支持
     * 0-不支持
     */
    @NotNull(message = "imp.ext.pcta cannot be empty")
    private Integer pcta;


}
