package com.leeyom.scaffold.dto.resp;

import lombok.Data;

import java.math.BigDecimal;
import java.util.List;

@Data
public class Bid {
    private String id;

    private String impid;

    private BigDecimal price;

    private String nurl; //竞价成功通知地址

    private String lurl; //竞价失败通知地址

    private String adm;

    private String burl; //竞价通知地址

    private List<String> adomain; // Advertiser domains for block list checking

    private String bundle;

    private String cid;

    private String crid;

    private List<Integer> attr;

    private List<String> cat;

    private Integer api;

    private BidExt ext;

    private String adid;
}
