package com.leeyom.scaffold.dto.req;

import lombok.Data;

import java.util.List;

@Data
public class Companionad {
    private String id;

    private List<Format> format;

    private Integer w;
    private Integer h;

    private Integer pos;

    private List<Integer> api;

    private Integer vcm;
}
