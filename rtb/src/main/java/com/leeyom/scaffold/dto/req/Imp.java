package com.leeyom.scaffold.dto.req;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;

@Data
public class Imp {
    @NotBlank(message = "imp.id cannot be empty")
    private String id;

    private Banner banner;

    private Video video;

    /**
     * JzTech ios
     * JzTechDroid Android
     * JzTechWindows Windows
     */
    @NotBlank(message = "imp.displaymanager cannot be empty")
    private String displaymanager;


    @NotBlank(message = "imp.displaymanagerver cannot be empty")
    private String displaymanagerver;

    private Integer instl;

    /**
     * 曝光位置id
     */
    @NotBlank(message = "imp.tagid cannot be empty")
    private String tagid;

    /**
     * 最低投标价格
     */
    @NotNull(message = "imp.bidfloor cannot be empty")
    private Integer bidfloor;

    /**
     * 货币单位：USD
     */
    @NotBlank(message = "imp.bidfloorcur cannot be empty")
    private String bidfloorcur;

    /**
     * 固定1-安全
     */
    @NotNull(message = "imp.secure cannot be empty")
    private Integer secure;

    private ImpExt ext;

}
