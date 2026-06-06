package com.leeyom.scaffold.dto.req;

import lombok.Data;

import javax.validation.constraints.NotNull;
import java.util.List;

@Data
public class Video {

    private List<String> mimes;

    private Integer minduration;

    private Integer maxduration;

    @NotNull(message = "")
    private List<Integer> protocols;

    @NotNull(message = "")
    private Integer w;

    @NotNull(message = "")
    private Integer h;

    @NotNull(message = "")
    private Integer placement;

    private Integer plcmt;

    private Integer linearity;

    private Integer skip;

    private Integer skipafter;

    @NotNull(message = "")
    private Integer minbitrate;

    @NotNull(message = "")
    private Integer maxbitrate;

    @NotNull(message = "")
    private Integer boxingallowed;

    @NotNull(message = "")
    private List<Integer> playbackmethod;

    @NotNull(message = "")
    private List<Integer> delivery;

    private Integer pos;

    private List<Companionad> companionad;

    private List<Integer> api;

    private List<Integer> companiontype;

    private DeviceExt ext;


}
