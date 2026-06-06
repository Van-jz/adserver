package com.leeyom.scaffold.dto.resp;

import lombok.Data;

import java.util.List;

@Data
public class BidExt {
    private Skadn skadn;
    private String deeplink;
    private List<String> imptrackers;
    private String crtype;
}
