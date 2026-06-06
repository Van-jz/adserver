package com.leeyom.scaffold.dto.req;

import lombok.Data;

@Data
public class DeviceExt {
    private String idfv;

    private String ifv;

    /**
     * 应用程序跟踪授权状态(ios适用)
     * 0=未确定
     * 1=受限
     * 2=拒绝
     * 3=授权
     */
    private Integer atts;

    /**
     * Android应用程序集ID
     */
    private String app_set_id;

    /**
     * 1=应用程序范围，2=开发人员范围
     */
    private String app_set_id_scope;
}
