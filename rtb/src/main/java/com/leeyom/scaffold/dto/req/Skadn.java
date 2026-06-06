package com.leeyom.scaffold.dto.req;

import com.leeyom.scaffold.dto.resp.SkadnExt;
import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotEmpty;
import java.util.List;

@Data
public class Skadn {
    @NotBlank(message = "imp.ext.skadn.version cannot empty")
    private String version;

    @NotEmpty(message = "imp.ext.skadn.versions cannot empty")
    private List<String> versions;

    @NotBlank(message = "imp.ext.skadn.sourceapp cannot empty")
    private String sourceapp;

    @NotEmpty(message = "imp.ext.skadn.skadnetids cannot empty")
    private List<String> skadnetids;

    private SkadnExt ext;
}
