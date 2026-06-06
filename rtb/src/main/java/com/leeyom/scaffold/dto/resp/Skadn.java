package com.leeyom.scaffold.dto.resp;

import lombok.Data;

@Data
public class Skadn {
    private String version;
    private String network;
    private String campaign;
    private String itunesitem;
    private String nonce;
    private String sourceapp;
    private String timestamp;
    private String signature;
    private SkadnExt ext;
}
