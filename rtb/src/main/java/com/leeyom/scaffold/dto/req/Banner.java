package com.leeyom.scaffold.dto.req;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import java.util.List;

@Data
public class Banner {

    @NotBlank(message = "")
    private String id;

    @NotNull(message = "")
    private List<Format> format;

    @NotNull(message = "")
    private Integer w;

    @NotNull(message = "")
    private Integer h;

    private Integer pos;

    @NotNull(message = "")
    private List<String> mimes;


    private List<Integer> api;

    private Integer vcm;

}
