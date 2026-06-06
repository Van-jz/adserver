package com.leeyom.scaffold.dto.req;

import lombok.Data;

import javax.validation.constraints.NotBlank;

@Data
public class Device {

    @NotBlank(message = "device.ua cannot be empty")
    private String ua;

    private Geo geo;

    private Integer dnt;

    private Integer lmt;

    /**
     * ip 和ipv6 不能同时为空
     */
    private String ip;

    /**
     * ip 和ipv6 不能同时为空
     */
    private String ipv6;

    /**
     * 1 Mobile/Tablet Version 2.0
     * 2 Personal Computer Version 2.0
     * 3 Connected TV Version 2.0
     * 4 Phone New for Version 2.2
     * 5 Tablet New for Version 2.2
     * 6 Connected Device New for Version 2.2
     * 7 Set Top Box New for Version 2.2
     */
    private Integer devicetype;

    private String make;

    private String model;

    /**
     * - 'iOS'
     * - 'Android'
     * - 'Windows'
     */
    private String os;

    private String osv;

    /**
     * 高度
     */
    @NotBlank(message = "device.h cannot be empty")
    private Integer h;

    /**
     * 宽度
     */
    @NotBlank(message = "device.w cannot be empty")
    private Integer w;

    private String language;

    /**
     * 连接方式
     * 0 Unknown
     * 1 Ethernet
     * 2 WIFI
     * 3 Cellular Network – Unknown Generation
     * 4 Cellular Network – 2G
     * 5 Cellular Network – 3G
     * 6 Cellular Network – 4G
     */
    @NotBlank(message = "device.connectiontype cannot be empty")
    private Integer connectiontype;

    private String ifa;

    private String dpidsha1;

    private DeviceExt ext;
}
