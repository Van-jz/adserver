package com.leeyom.scaffold.dto.req;

import lombok.Data;

import java.util.List;

@Data
public class Schain {

    private Integer complete;

    private List<Nodes> nodes;

    private String ver;

}
