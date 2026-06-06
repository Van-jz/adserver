package com.leeyom.scaffold.dto.req;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import java.math.BigDecimal;

@Data
public class Geo {

    private BigDecimal lat;

    private BigDecimal lon;

    private Integer type;

    @NotNull(message = "device.geo.ipservice cannot empty")
    private Integer ipservice;

    /**
     * 例如：USA
     */
    @NotBlank(message = "device.geo.country cannot empty")
    private String country;

    private String region;

    private String city;

    private String zip;

}
