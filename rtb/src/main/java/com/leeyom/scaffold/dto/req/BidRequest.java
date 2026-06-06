package com.leeyom.scaffold.dto.req;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import java.util.List;

@Data
public class BidRequest {
    @NotBlank(message = "id cannot be empty")
    private String id;

    @NotNull(message = "imp cannot be empty")
    private List<Imp> imp;

    @NotNull(message = "app cannot be empty")
    private App app;

    @NotNull(message = "device cannot be empty")
    private Device device;

    private User user;

    /**
     * 拍卖类型（固定1）
     * 2 表示第二价格拍卖。
     */
    @NotNull(message = "at cannot be empty")
    private Integer at;

    /**
     * 投标完成响应的最大毫秒数
     */
    @NotNull(message = "tmax cannot be empty")
    private Integer tmax;

    /**
     * 仅支持 USD
     */
    private List<String> cur;

    /**
     * Content Categories
     */
    private List<String> bcat;

    /**
     * 按域名屏蔽广告商列表
     */
    private List<String> badv;

    /**
     * 按照包名（安卓）或者 appstroeid（ios）屏蔽广告商列表
     */
    private List<String> bapp;

//    @NotNull(message = "source cannot be empty")
    private Source source;

    private Regs regs;

    private ReqExt ext;
}
